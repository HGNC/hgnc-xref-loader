"""Alphafold load service.

Orchestrates the Alphafold accession ID mapping load pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.alphafold_parser import AlphafoldParser

logger = logging.getLogger(__name__)

ALPHAFOLD_URL = "http://ftp.ebi.ac.uk/pub/databases/alphafold/accession_ids.csv"
ALPHAFOLD_TABLE = "alphafold"
ALPHAFOLD_STAGING = "alphafold_update"


@dataclass
class AlphafoldLoadResult:
    """Outcome of an alphafold load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class AlphafoldLoadService:
    """Orchestrate the Alphafold load pipeline.

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
        self._parser = AlphafoldParser()

    def run(self) -> AlphafoldLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``AlphafoldLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                ALPHAFOLD_TABLE, self._source_version
            ):
                return AlphafoldLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=ALPHAFOLD_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(ALPHAFOLD_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                ALPHAFOLD_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                ALPHAFOLD_STAGING, ALPHAFOLD_TABLE
            )

            self._version_tracker.record_version(
                ALPHAFOLD_TABLE, self._source_version
            )

            logger.info(
                "alphafold_load_complete",
                extra={"rows_loaded": count},
            )

            return AlphafoldLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "alphafold_load_failed",
                extra={"error": str(exc)},
            )
            return AlphafoldLoadResult(success=False, error=str(exc))
