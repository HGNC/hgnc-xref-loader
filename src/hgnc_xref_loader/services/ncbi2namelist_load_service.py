"""NCBI to NameList load service.

Orchestrates the NCBI to_name load pipeline: FTP download, parsing,
staging, and promotion.

Note: The source is on a private FTP server requiring credentials.
The fetch client must handle authentication.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.ncbi2namelist_parser import Ncbi2NamelistParser

logger = logging.getLogger(__name__)

NCBI2NAMELIST_TABLE = "ncbi2namelist"
NCBI2NAMELIST_STAGING = "ncbi2namelist_update"


@dataclass
class Ncbi2NamelistLoadResult:
    """Outcome of an ncbi2namelist load run.

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


class Ncbi2NamelistLoadService:
    """Orchestrate the NCBI to_name load pipeline.

    Args:
        fetch_client: FTP download client with authentication.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current source version string.
    """

    def __init__(
        self,
        fetch_client: Any,
        staging_repo: Any,
        version_tracker: Any,
        source_version: str = "",
    ) -> None:
        self._fetch_client = fetch_client
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._source_version = source_version
        self._parser = Ncbi2NamelistParser()

    def run(self) -> Ncbi2NamelistLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``Ncbi2NamelistLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                NCBI2NAMELIST_TABLE, self._source_version
            ):
                return Ncbi2NamelistLoadResult(success=True, skipped=True)

            data = self._fetch_client.fetch()

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(NCBI2NAMELIST_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                NCBI2NAMELIST_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                NCBI2NAMELIST_STAGING, NCBI2NAMELIST_TABLE
            )

            self._version_tracker.record_version(
                NCBI2NAMELIST_TABLE, self._source_version
            )

            logger.info(
                "ncbi2namelist_load_complete",
                extra={"rows_loaded": count},
            )

            return Ncbi2NamelistLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "ncbi2namelist_load_failed",
                extra={"error": str(exc)},
            )
            return Ncbi2NamelistLoadResult(success=False, error=str(exc))
