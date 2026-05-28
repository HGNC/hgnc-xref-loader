"""RNA Central load service.

Orchestrates the RNAcentral id_mapping load pipeline: FTP download, gzip
decompression, parsing, staging, and promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.rna_central_parser import RnaCentralParser

logger = logging.getLogger(__name__)

RNA_CENTRAL_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/RNAcentral/"
    "current_release/id_mapping/id_mapping.tsv.gz"
)
RNA_CENTRAL_TABLE = "rna_central"
RNA_CENTRAL_STAGING = "rna_central_update"


@dataclass
class RnaCentralLoadResult:
    """Outcome of an rna_central load run.

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


class RnaCentralLoadService:
    """Orchestrate the RNAcentral id_mapping load pipeline.

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
        self._parser = RnaCentralParser()

    def run(self) -> RnaCentralLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``RnaCentralLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                RNA_CENTRAL_TABLE, self._source_version
            ):
                return RnaCentralLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=RNA_CENTRAL_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(RNA_CENTRAL_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                RNA_CENTRAL_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                RNA_CENTRAL_STAGING, RNA_CENTRAL_TABLE
            )

            self._version_tracker.record_version(
                RNA_CENTRAL_TABLE, self._source_version
            )

            logger.info(
                "rna_central_load_complete",
                extra={"rows_loaded": count},
            )

            return RnaCentralLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "rna_central_load_failed",
                extra={"error": str(exc)},
            )
            return RnaCentralLoadResult(success=False, error=str(exc))
