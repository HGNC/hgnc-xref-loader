"""LOVD load service.

Orchestrates the LOVD (Leiden Open Variation Database) load pipeline:
HTTP scrape, parse, stage, and promote.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

LOVD_URL = "http://www.lovd.nl/2.0/index_list.php?export=txt"
LOVD_TABLE = "lovd"
LOVD_STAGING = "lovd_update"


@dataclass
class LovdLoadResult:
    """Outcome of a LOVD load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class LovdLoadService:
    """Orchestrate the LOVD load pipeline.

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

    def run(self) -> LovdLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``LovdLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                LOVD_TABLE, self._source_version
            ):
                return LovdLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=LOVD_URL)
            records = self._parse_lovd(data)

            self._staging_repo.prepare_staging_table(LOVD_TABLE)

            count = self._staging_repo.bulk_copy_into_staging(
                LOVD_STAGING, records
            )

            self._staging_repo.promote_staging_to_production(
                LOVD_STAGING, LOVD_TABLE
            )

            self._version_tracker.record_version(
                LOVD_TABLE, self._source_version
            )

            logger.info(
                "lovd_load_complete",
                extra={"rows_loaded": count},
            )

            return LovdLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "lovd_load_failed",
                extra={"error": str(exc)},
            )
            return LovdLoadResult(success=False, error=str(exc))

    @staticmethod
    def _parse_lovd(data: bytes) -> list[dict[str, str]]:
        """Parse LOVD tab-separated export data.

        Args:
            data: Raw text bytes from LOVD.

        Returns:
            List of dicts with lovd_db_name, lovd_db_url, lovd_db_genes.
        """
        text = data.decode("utf-8")
        records: list[dict[str, str]] = []

        for line in text.splitlines():
            cols = line.split("\t")
            if len(cols) < 3:
                continue

            db_name = cols[0].strip()
            db_url = cols[1].strip()
            db_genes = cols[2].strip()

            if not db_name:
                continue

            records.append({
                "lovd_db_name": db_name,
                "lovd_db_url": db_url,
                "lovd_db_genes": db_genes,
            })

        logger.info(
            "lovd_parsed",
            extra={"record_count": len(records)},
        )
        return records
