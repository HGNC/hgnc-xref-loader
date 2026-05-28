"""AGR load service.

Orchestrates the Alliance genome gene description load pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.agr_parser import AgrParser

logger = logging.getLogger(__name__)

AGR_URL = "http://reports.alliancegenome.org/gene-descriptions/HUMAN_gene_desc_latest.tsv"
AGR_TABLE = "agr"
AGR_STAGING = "agr_update"


@dataclass
class AgrLoadResult:
    """Outcome of an AGR load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class AgrLoadService:
    """Orchestrate the Alliance genome load pipeline.

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
        self._parser = AgrParser()

    def run(self) -> AgrLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``AgrLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(AGR_TABLE, self._source_version):
                return AgrLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=AGR_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(AGR_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                AGR_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                AGR_STAGING, AGR_TABLE
            )

            self._version_tracker.record_version(AGR_TABLE, self._source_version)

            logger.info(
                "agr_load_complete",
                extra={"rows_loaded": count},
            )

            return AgrLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "agr_load_failed",
                extra={"error": str(exc)},
            )
            return AgrLoadResult(success=False, error=str(exc))
