"""Omim2Gene load service.

Orchestrates the OMIM mim2gene load pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.omim2gene_parser import Omim2GeneParser

logger = logging.getLogger(__name__)

OMIM2GENE_URL = "https://www.omim.org/static/omim/data/mim2gene.txt"
OMIM2GENE_TABLE = "omim2gene"
OMIM2GENE_STAGING = "omim2gene_update"


@dataclass
class Omim2GeneLoadResult:
    """Outcome of an omim2gene load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class Omim2GeneLoadService:
    """Orchestrate the OMIM mim2gene load pipeline.

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
        self._parser = Omim2GeneParser()

    def run(self) -> Omim2GeneLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``Omim2GeneLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                OMIM2GENE_TABLE, self._source_version
            ):
                return Omim2GeneLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(url=OMIM2GENE_URL)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(OMIM2GENE_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                OMIM2GENE_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                OMIM2GENE_STAGING, OMIM2GENE_TABLE
            )

            self._version_tracker.record_version(
                OMIM2GENE_TABLE, self._source_version
            )

            logger.info(
                "omim2gene_load_complete",
                extra={"rows_loaded": count},
            )

            return Omim2GeneLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "omim2gene_load_failed",
                extra={"error": str(exc)},
            )
            return Omim2GeneLoadResult(success=False, error=str(exc))
