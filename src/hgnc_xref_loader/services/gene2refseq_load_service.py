"""Gene2Refseq load service.

Orchestrates the NCBI gene2refseq load pipeline: HTTP download, gzip
decompression, parsing, staging, and promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.gene2refseq_parser import Gene2RefseqParser

logger = logging.getLogger(__name__)

GENE2REFSEQ_TABLE = "gene2refseq"
GENE2REFSEQ_STAGING = "gene2refseq_update"


@dataclass
class Gene2RefseqLoadResult:
    """Outcome of a gene2refseq load run.

    Attributes:
        success: Whether the load completed without error.
        skipped: Whether the load was skipped (version unchanged).
        rows_loaded: Number of rows loaded into staging.
        error: Error message if the load failed.
    """

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class Gene2RefseqLoadService:
    """Orchestrate the NCBI gene2refseq load pipeline.

    Args:
        http_client: HTTP download client.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current source version string.
    """

    def __init__(
        self,
        http_client: Any,
        staging_repo: Any,
        version_tracker: Any,
        source_version: str = "",
    ) -> None:
        self._http_client = http_client
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._source_version = source_version
        self._parser = Gene2RefseqParser()

    def run(self) -> Gene2RefseqLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``Gene2RefseqLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                GENE2REFSEQ_TABLE, self._source_version
            ):
                return Gene2RefseqLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(
                url="https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2refseq.gz"
            )

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(GENE2REFSEQ_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                GENE2REFSEQ_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                GENE2REFSEQ_STAGING, GENE2REFSEQ_TABLE
            )

            self._version_tracker.record_version(
                GENE2REFSEQ_TABLE, self._source_version
            )

            logger.info(
                "gene2refseq_load_complete",
                extra={"rows_loaded": count},
            )

            return Gene2RefseqLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "gene2refseq_load_failed",
                extra={"error": str(exc)},
            )
            return Gene2RefseqLoadResult(success=False, error=str(exc))
