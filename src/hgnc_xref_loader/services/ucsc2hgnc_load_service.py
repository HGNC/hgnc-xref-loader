"""UCSC-to-HGNC load service.

Orchestrates the UCSC-to-HGNC mapping load pipeline: query UCSC MySQL,
stage with deduplication, and promote.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

UCSC2HGNC_TABLE = "ucsc2hgnc"
UCSC2HGNC_STAGING = "ucsc2hgnc_update"


@dataclass
class Ucsc2HgncLoadResult:
    """Outcome of a ucsc2hgnc load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class Ucsc2HgncLoadService:
    """Orchestrate the UCSC-to-HGNC mapping load pipeline.

    Args:
        ucsc_repo: Repository for UCSC data access.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current source version string.
    """

    def __init__(
        self,
        ucsc_repo: Any,
        staging_repo: Any,
        version_tracker: Any,
        source_version: str = "",
    ) -> None:
        self._ucsc_repo = ucsc_repo
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._source_version = source_version

    def run(self) -> Ucsc2HgncLoadResult:
        """Execute the fetch->stage->promote pipeline.

        Returns:
            A ``Ucsc2HgncLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                UCSC2HGNC_TABLE, self._source_version
            ):
                return Ucsc2HgncLoadResult(success=True, skipped=True)

            records = self._ucsc_repo.fetch_mappings()
            records = self._deduplicate(records)

            self._staging_repo.prepare_staging_table(UCSC2HGNC_TABLE)

            count = self._staging_repo.bulk_copy_into_staging(
                UCSC2HGNC_STAGING, records
            )

            self._staging_repo.promote_staging_to_production(
                UCSC2HGNC_STAGING, UCSC2HGNC_TABLE
            )

            self._version_tracker.record_version(
                UCSC2HGNC_TABLE, self._source_version
            )

            logger.info(
                "ucsc2hgnc_load_complete",
                extra={"rows_loaded": count},
            )

            return Ucsc2HgncLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "ucsc2hgnc_load_failed",
                extra={"error": str(exc)},
            )
            return Ucsc2HgncLoadResult(success=False, error=str(exc))

    @staticmethod
    def _deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Mark first occurrence of each HGNC ID as 'M', subsequent as '-'.

        Args:
            records: List of staging dicts.

        Returns:
            Records with deduplicated ucsc_mapby field.
        """
        seen: set[str] = set()
        for record in records:
            hgnc_id = str(record.get("ucsc_hgnc_id", ""))
            if hgnc_id in seen:
                record["ucsc_mapby"] = "-"
            else:
                record["ucsc_mapby"] = "M"
                seen.add(hgnc_id)
        return records
