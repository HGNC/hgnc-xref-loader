"""Abstract interface and domain exceptions for the xref staging repository.

Defines the staging-table lifecycle contract used by xref loader services:
prepare staging table, bulk COPY load, create indexes, validate row counts,
and atomically promote staging to production. All DDL is confined to concrete
implementations of this interface; services never execute SQL/DDL.
"""

from __future__ import annotations

from abc import abstractmethod

from hgnc_xref_loader.exceptions import RepositoryError
from hgnc_xref_loader.repositories.base_repository import Repository


class StagingPromotionError(RepositoryError):
    """Raised when a staging-to-production promotion fails.

    Carries the staging and source table names for diagnostic context.
    """

    def __init__(self, staging_table: str, source_table: str, message: str = "") -> None:
        self.staging_table = staging_table
        self.source_table = source_table
        detail = message or f"Promotion failed for staging={staging_table} source={source_table}"
        super().__init__(detail)


class RowCountMismatchError(StagingPromotionError):
    """Raised when staging row count does not match expected count.

    Carries the expected and actual row counts alongside table context.
    """

    def __init__(
        self,
        staging_table: str,
        expected: int,
        actual: int,
    ) -> None:
        self.expected_count = expected
        self.actual_count = actual
        msg = (
            f"Row count mismatch for {staging_table}: "
            f"expected {expected}, got {actual}"
        )
        super().__init__(
            staging_table=staging_table,
            source_table="",
            message=msg,
        )


class XrefStagingRepository(Repository):
    """Abstract base class for xref staging-table lifecycle operations.

    Defines the contract for preparing staging tables, performing bulk COPY
    loads, creating indexes, validating row counts, and atomically promoting
    a staging table to production. Implementations MUST confine all DDL to
    repository methods and use safe identifier composition APIs.

    The staging-table naming convention is ``{source_table}_update``. Promotion
    swaps this staging table into the production ``{source_table}`` name via
    ``ALTER TABLE ... RENAME``, updating ``table_mod_dates`` atomically.

    Services depend on this abstraction; they never execute SQL or DDL.
    """

    @abstractmethod
    def prepare_staging_table(self, source_table: str) -> str:
        """Drop and recreate the staging table for the given source.

        Creates a clean ``{source_table}_update`` staging table, destroying
        any prior staging data. This ensures deterministic re-run behavior:
        every load starts from a known empty state.

        Args:
            source_table: Production table name (e.g. ``entrez_gene_2_accession``).

        Returns:
            The staging table name (``{source_table}_update``).
        """

    @abstractmethod
    def bulk_copy_into_staging(self, staging_table: str, records: list[dict]) -> int:
        """Bulk-load records into the staging table using psycopg v3 COPY.

        Uses COPY for maximum throughput. Accepts an empty record list
        without error (zero-row sources are valid).

        Args:
            staging_table: Name of the staging table to load into.
            records: List of dictionaries representing rows to insert.

        Returns:
            The number of rows loaded (0 for empty input).
        """

    @abstractmethod
    def create_staging_indexes(self, staging_table: str, source_table: str) -> None:
        """Create indexes on the staging table matching production schema.

        Creates the same indexes that exist on the production table so
        that post-promotion query performance is maintained.

        Args:
            staging_table: Name of the staging table.
            source_table: Production table whose indexes to replicate.
        """

    @abstractmethod
    def validate_staging_row_count(
        self,
        staging_table: str,
        expected_count: int,
    ) -> None:
        """Assert staging table row count matches the expected count.

        Raises ``RowCountMismatchError`` if the counts differ. This guard
        catches partial or corrupted loads before promotion.

        Args:
            staging_table: Name of the staging table to validate.
            expected_count: Expected number of rows in the staging table.

        Raises:
            RowCountMismatchError: If actual count differs from expected.
        """

    @abstractmethod
    def promote_staging_to_production(
        self,
        staging_table: str,
        source_table: str,
    ) -> None:
        """Atomically promote the staging table to production.

        Renames ``{staging_table}`` to ``{source_table}`` and updates
        ``table_mod_dates`` within the same transaction. On failure, the
        transaction rolls back and the previous production table is preserved.

        Args:
            staging_table: Name of the staging table to promote.
            source_table: Target production table name.

        Raises:
            StagingPromotionError: If the promotion DDL fails.
        """
