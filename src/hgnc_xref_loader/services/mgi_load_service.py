"""MGI load service.

Orchestrates the MGI Alliance homology report load pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.mgi_parser import MgiParser

logger = logging.getLogger(__name__)

MGI_URL = "http://www.informatics.jax.org/downloads/reports/HGNC_AllianceHomology.rpt"
MGI_TABLE = "mgi"
MGI_STAGING = "mgi_update"


@dataclass
class MgiLoadResult:
    """Outcome of an MGI load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class MgiLoadService:
    """Orchestrate the MGI homology report load pipeline.

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
        self._parser = MgiParser()

    def run(self) -> MgiLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``MgiLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(MGI_TABLE, self._source_version):
                return MgiLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=MGI_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(MGI_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                MGI_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                MGI_STAGING, MGI_TABLE
            )

            self._version_tracker.record_version(MGI_TABLE, self._source_version)

            logger.info(
                "mgi_load_complete",
                extra={"rows_loaded": count},
            )

            return MgiLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "mgi_load_failed",
                extra={"error": str(exc)},
            )
            return MgiLoadResult(success=False, error=str(exc))
