"""Cytoband load service.

Orchestrates the cytoband load pipeline: query UCSC/Ensembl databases,
stage, and promote. Cytoband data comes from the genew4 database via
raw SQL (not from an external download).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

CYTOBAND_TABLE = "cytoband"
CYTOBAND_STAGING = "cytoband_update"


@dataclass
class CytobandLoadResult:
    """Outcome of a cytoband load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class CytobandLoadService:
    """Orchestrate the cytoband load pipeline.

    Cytoband data is sourced from the UCSC and Ensembl databases via
    the genew4 database raw SQL interface.

    Args:
        cytoband_repo: Repository for cytoband data access.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current source version string.
    """

    def __init__(
        self,
        cytoband_repo: Any,
        staging_repo: Any,
        version_tracker: Any,
        source_version: str = "",
    ) -> None:
        self._cytoband_repo = cytoband_repo
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._source_version = source_version

    def run(self) -> CytobandLoadResult:
        """Execute the fetch->stage->promote pipeline.

        Returns:
            A ``CytobandLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                CYTOBAND_TABLE, self._source_version
            ):
                return CytobandLoadResult(success=True, skipped=True)

            records = self._cytoband_repo.fetch_cytobands()

            self._staging_repo.prepare_staging_table(CYTOBAND_TABLE)

            count = self._staging_repo.bulk_copy_into_staging(
                CYTOBAND_STAGING, records
            )

            self._staging_repo.promote_staging_to_production(
                CYTOBAND_STAGING, CYTOBAND_TABLE
            )

            self._version_tracker.record_version(
                CYTOBAND_TABLE, self._source_version
            )

            logger.info(
                "cytoband_load_complete",
                extra={"rows_loaded": count},
            )

            return CytobandLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "cytoband_load_failed",
                extra={"error": str(exc)},
            )
            return CytobandLoadResult(success=False, error=str(exc))
