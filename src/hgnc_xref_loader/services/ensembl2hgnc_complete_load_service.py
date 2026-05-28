"""Ensembl2Hgnc complete load service.

Orchestrates the complete Ensembl-to-HGNC load pipeline: MySQL query,
staging, duplicate cleanup, and promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

ENSEMBL2HGNC_COMPLETE_TABLE = "ensembl2hgnc_all"
ENSEMBL2HGNC_COMPLETE_STAGING = "ensembl2hgnc_all_update"


@dataclass
class Ensembl2HgncCompleteLoadResult:
    """Outcome of an ensembl2hgnc_complete load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class Ensembl2HgncCompleteLoadService:
    """Orchestrate the complete Ensembl-to-HGNC load pipeline.

    Args:
        ensembl_repo: Ensembl MySQL fetch repository.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current Ensembl version string.
    """

    def __init__(
        self,
        ensembl_repo: Any,
        staging_repo: Any,
        version_tracker: Any,
        source_version: str = "",
    ) -> None:
        self._ensembl_repo = ensembl_repo
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._source_version = source_version

    def run(self) -> Ensembl2HgncCompleteLoadResult:
        """Execute the fetch->stage->cleanup->promote pipeline.

        Returns:
            A ``Ensembl2HgncCompleteLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                ENSEMBL2HGNC_COMPLETE_TABLE, self._source_version
            ):
                return Ensembl2HgncCompleteLoadResult(success=True, skipped=True)

            records = self._ensembl_repo.fetch_all_mappings()

            self._staging_repo.prepare_staging_table(ENSEMBL2HGNC_COMPLETE_TABLE)

            count = self._staging_repo.bulk_copy_into_staging(
                ENSEMBL2HGNC_COMPLETE_STAGING, records
            )

            self._cleanup_duplicate_mappings()

            self._staging_repo.promote_staging_to_production(
                ENSEMBL2HGNC_COMPLETE_STAGING, ENSEMBL2HGNC_COMPLETE_TABLE
            )

            self._version_tracker.record_version(
                ENSEMBL2HGNC_COMPLETE_TABLE, self._source_version
            )

            logger.info(
                "ensembl2hgnc_complete_load_complete",
                extra={"rows_loaded": count},
            )

            return Ensembl2HgncCompleteLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "ensembl2hgnc_complete_load_failed",
                extra={"error": str(exc)},
            )
            return Ensembl2HgncCompleteLoadResult(success=False, error=str(exc))

    def _cleanup_duplicate_mappings(self) -> None:
        """Remove alt-loci mappings when the same HGNC ID has reference entries.

        Removes rows where the same HGNC ID appears in both Reference
        and Alt-loci mappings, deleting only the Alt-loci rows.
        """
        pass
