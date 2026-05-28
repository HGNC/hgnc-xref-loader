"""Ensembl2Hgnc load service orchestrating MySQL fetch, staging, and promotion.

Coordinates the Ensembl2Hgnc pipeline: fetch mappings from Ensembl MySQL,
stage into the Postgres ``ensembl2hgnc_update`` table, perform duplicate
cleanup (remove HGNC IDs mapping to multiple distinct Ensembl gene IDs),
and promote to production.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.repositories.ensembl2hgnc_repository import (
    ENSEMBL2HGNC_STAGING_COLUMNS,
    ENSEMBL2HGNC_STAGING_TABLE,
    Ensembl2HgncRepository,
)
from psycopg import sql

logger = logging.getLogger(__name__)

CLEANUP_SQL_TEMPLATE = (
    "DELETE FROM {staging_table} "
    "WHERE {hgnc_id_col} IN ("
    "  SELECT a.{hgnc_id_col}"
    "  FROM {staging_table} a, {staging_table} b"
    "  WHERE a.{hgnc_id_col} = b.{hgnc_id_col}"
    "  AND a.{ensembl_gene_id_col} != b.{ensembl_gene_id_col}"
    ")"
)


@dataclass
class Ensembl2HgncLoadResult:
    """Outcome of an Ensembl2Hgnc load run.

    Attributes:
        success: Whether the load completed without error.
        skipped: Whether the load was skipped (version unchanged).
        rows_loaded: Number of rows loaded into staging.
        error: Error message if the load failed.
    """

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class Ensembl2HgncLoadService:
    """Orchestrate the Ensembl2Hgnc load pipeline.

    Fetches Ensembl-to-HGNC mappings from Ensembl MySQL, stages into
    Postgres, performs duplicate cleanup, and promotes to production.

    Args:
        ensembl_repo: Repository for Ensembl MySQL queries.
        staging_repo: Repository for Postgres staging/promotion operations.
        version_tracker: Version tracking service.
        ensembl_version: Current Ensembl release version string.
    """

    def __init__(
        self,
        ensembl_repo: Ensembl2HgncRepository,
        staging_repo: Any,
        version_tracker: Any,
        ensembl_version: str,
    ) -> None:
        self._ensembl_repo = ensembl_repo
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._ensembl_version = ensembl_version

    def run(self) -> Ensembl2HgncLoadResult:
        """Execute the full fetch->stage->cleanup->promote pipeline.

        Returns:
            An ``Ensembl2HgncLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                "ensembl2hgnc", self._ensembl_version
            ):
                return Ensembl2HgncLoadResult(success=True, skipped=True)

            records = self._ensembl_repo.fetch_mappings()

            self._staging_repo.prepare_staging_table("ensembl2hgnc")

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                ENSEMBL2HGNC_STAGING_TABLE, staging_dicts
            )

            self._staging_repo.execute_cleanup(self.get_cleanup_sql())

            self._staging_repo.promote_staging_to_production(
                ENSEMBL2HGNC_STAGING_TABLE, "ensembl2hgnc"
            )

            self._version_tracker.record_version(
                "ensembl2hgnc", self._ensembl_version
            )

            logger.info(
                "ensembl2hgnc_load_complete",
                extra={"rows_loaded": count, "version": self._ensembl_version},
            )

            return Ensembl2HgncLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "ensembl2hgnc_load_failed",
                extra={"error": str(exc)},
            )
            return Ensembl2HgncLoadResult(success=False, error=str(exc))

    def get_cleanup_sql(self) -> str:
        """Return the duplicate cleanup SQL for the staging table.

        The cleanup deletes all rows for HGNC IDs that map to multiple
        distinct Ensembl gene IDs, matching the Perl reference logic.

        Returns:
            A SQL string for execution against the staging table.
        """
        return CLEANUP_SQL_TEMPLATE.format(
            staging_table=ENSEMBL2HGNC_STAGING_TABLE,
            hgnc_id_col="e2h_hgnc_id",
            ensembl_gene_id_col="e2h_ensembl_gene_id",
        )
