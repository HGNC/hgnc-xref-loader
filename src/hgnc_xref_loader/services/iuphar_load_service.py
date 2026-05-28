"""IUPHAR load service.

Orchestrates the IUPHAR/GtoP HGNC mapping load pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.iuphar_parser import IupharParser

logger = logging.getLogger(__name__)

IUPHAR_URL = "https://www.guidetopharmacology.org/DATA/GtP_to_HGNC_mapping.csv"
IUPHAR_TABLE = "iuphar"
IUPHAR_STAGING = "iuphar_update"


@dataclass
class IupharLoadResult:
    """Outcome of an iuphar load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class IupharLoadService:
    """Orchestrate the IUPHAR load pipeline.

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
        self._parser = IupharParser()

    def run(self) -> IupharLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``IupharLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                IUPHAR_TABLE, self._source_version
            ):
                return IupharLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=IUPHAR_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(IUPHAR_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                IUPHAR_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                IUPHAR_STAGING, IUPHAR_TABLE
            )

            self._version_tracker.record_version(
                IUPHAR_TABLE, self._source_version
            )

            logger.info(
                "iuphar_load_complete",
                extra={"rows_loaded": count},
            )

            return IupharLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "iuphar_load_failed",
                extra={"error": str(exc)},
            )
            return IupharLoadResult(success=False, error=str(exc))
