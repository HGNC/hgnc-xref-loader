"""Ensembl gene load service.

Orchestrates the Ensembl gene load pipeline: MySQL query, staging, promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

ENSEMBL_GENE_TABLE = "ensembl_gene"
ENSEMBL_GENE_STAGING = "ensembl_gene_update"


@dataclass
class EnsemblGeneLoadResult:
    """Outcome of an ensembl_gene load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class EnsemblGeneLoadService:
    """Orchestrate the Ensembl gene load pipeline.

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

    def run(self) -> EnsemblGeneLoadResult:
        """Execute the fetch->stage->promote pipeline.

        Returns:
            A ``EnsemblGeneLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                ENSEMBL_GENE_TABLE, self._source_version
            ):
                return EnsemblGeneLoadResult(success=True, skipped=True)

            records = self._ensembl_repo.fetch_genes()

            self._staging_repo.prepare_staging_table(ENSEMBL_GENE_TABLE)

            count = self._staging_repo.bulk_copy_into_staging(
                ENSEMBL_GENE_STAGING, records
            )

            self._staging_repo.promote_staging_to_production(
                ENSEMBL_GENE_STAGING, ENSEMBL_GENE_TABLE
            )

            self._version_tracker.record_version(
                ENSEMBL_GENE_TABLE, self._source_version
            )

            logger.info(
                "ensembl_gene_load_complete",
                extra={"rows_loaded": count},
            )

            return EnsemblGeneLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "ensembl_gene_load_failed",
                extra={"error": str(exc)},
            )
            return EnsemblGeneLoadResult(success=False, error=str(exc))
