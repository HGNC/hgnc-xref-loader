"""Gene info load service.

Orchestrates the NCBI gene_info load pipeline: HTTP download, gzip
decompression, parsing, staging, and promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.gene_info_parser import GeneInfoParser

logger = logging.getLogger(__name__)

GENE_INFO_TABLE = "gene_info"
GENE_INFO_STAGING = "gene_info_update"


@dataclass
class GeneInfoLoadResult:
    """Outcome of a gene_info load run.

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


class GeneInfoLoadService:
    """Orchestrate the NCBI gene_info load pipeline.

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
        self._parser = GeneInfoParser()

    def run(self) -> GeneInfoLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``GeneInfoLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(GENE_INFO_TABLE, self._source_version):
                return GeneInfoLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(
                url="https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz"
            )

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(GENE_INFO_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                GENE_INFO_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                GENE_INFO_STAGING, GENE_INFO_TABLE
            )

            self._version_tracker.record_version(
                GENE_INFO_TABLE, self._source_version
            )

            logger.info(
                "gene_info_load_complete",
                extra={"rows_loaded": count},
            )

            return GeneInfoLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "gene_info_load_failed",
                extra={"error": str(exc)},
            )
            return GeneInfoLoadResult(success=False, error=str(exc))
