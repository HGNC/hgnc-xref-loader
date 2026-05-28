"""miRNA raw load service.

Orchestrates the miRBase GFF3 load pipeline: HTTP download, parsing,
staging, and promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.mirna_raw_parser import MirnaRawParser

logger = logging.getLogger(__name__)

MIRNA_RAW_URL = "https://www.mirbase.org/download/hsa.gff3"
MIRNA_RAW_TABLE = "mirna_raw"
MIRNA_RAW_STAGING = "mirna_raw_update"


@dataclass
class MirnaRawLoadResult:
    """Outcome of a mirna_raw load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class MirnaRawLoadService:
    """Orchestrate the miRBase GFF3 load pipeline.

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
        self._parser = MirnaRawParser()

    def run(self) -> MirnaRawLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``MirnaRawLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                MIRNA_RAW_TABLE, self._source_version
            ):
                return MirnaRawLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=MIRNA_RAW_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(MIRNA_RAW_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                MIRNA_RAW_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                MIRNA_RAW_STAGING, MIRNA_RAW_TABLE
            )

            self._version_tracker.record_version(
                MIRNA_RAW_TABLE, self._source_version
            )

            logger.info(
                "mirna_raw_load_complete",
                extra={"rows_loaded": count},
            )

            return MirnaRawLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "mirna_raw_load_failed",
                extra={"error": str(exc)},
            )
            return MirnaRawLoadResult(success=False, error=str(exc))
