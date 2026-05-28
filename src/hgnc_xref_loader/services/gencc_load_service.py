"""GenCC load service.

Orchestrates the GenCC load pipeline: HTTP CSV download, parsing,
staging, and promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.gencc_parser import GenCCParser

logger = logging.getLogger(__name__)

GENCC_URL = "https://search.thegencc.org/download/action/submissions-export-csv"
GENCC_TABLE = "gencc"
GENCC_STAGING = "gencc_update"


@dataclass
class GenCCLoadResult:
    """Outcome of a gencc load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class GenCCLoadService:
    """Orchestrate the GenCC load pipeline.

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
        self._parser = GenCCParser()

    def run(self) -> GenCCLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``GenCCLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                GENCC_TABLE, self._source_version
            ):
                return GenCCLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=GENCC_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(GENCC_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                GENCC_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                GENCC_STAGING, GENCC_TABLE
            )

            self._version_tracker.record_version(
                GENCC_TABLE, self._source_version
            )

            logger.info(
                "gencc_load_complete",
                extra={"rows_loaded": count},
            )

            return GenCCLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "gencc_load_failed",
                extra={"error": str(exc)},
            )
            return GenCCLoadResult(success=False, error=str(exc))
