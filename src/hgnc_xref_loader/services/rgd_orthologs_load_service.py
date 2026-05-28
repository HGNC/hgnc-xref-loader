"""RGD Orthologs load service.

Orchestrates the RGD orthologs load pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.rgd_orthologs_parser import RgdOrthologsParser

logger = logging.getLogger(__name__)

RGD_ORTHOLOGS_URL = "https://download.rgd.mcw.edu/pub/data_release/orthologs/RGD_ORTHOLOGS.txt"
RGD_ORTHOLOGS_TABLE = "rgd_orthologs"
RGD_ORTHOLOGS_STAGING = "rgd_orthologs_update"


@dataclass
class RgdOrthologsLoadResult:
    """Outcome of an rgd_orthologs load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class RgdOrthologsLoadService:
    """Orchestrate the RGD orthologs load pipeline.

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
        self._parser = RgdOrthologsParser()

    def run(self) -> RgdOrthologsLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``RgdOrthologsLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                RGD_ORTHOLOGS_TABLE, self._source_version
            ):
                return RgdOrthologsLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=RGD_ORTHOLOGS_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(RGD_ORTHOLOGS_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                RGD_ORTHOLOGS_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                RGD_ORTHOLOGS_STAGING, RGD_ORTHOLOGS_TABLE
            )

            self._version_tracker.record_version(
                RGD_ORTHOLOGS_TABLE, self._source_version
            )

            logger.info(
                "rgd_orthologs_load_complete",
                extra={"rows_loaded": count},
            )

            return RgdOrthologsLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "rgd_orthologs_load_failed",
                extra={"error": str(exc)},
            )
            return RgdOrthologsLoadResult(success=False, error=str(exc))
