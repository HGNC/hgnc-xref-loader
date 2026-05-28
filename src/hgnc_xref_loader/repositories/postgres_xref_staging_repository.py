"""Postgres implementation of the xref staging repository.

Provides concrete staging-table lifecycle operations using psycopg v3 COPY
for bulk loads, psycopg.sql.Identifier for safe dynamic identifier composition,
and atomic ALTER TABLE ... RENAME for staging-to-production promotion.

DDL is strictly scoped to the loader exception: DROP/CREATE on *_update
staging tables and ALTER TABLE ... RENAME for promotion. All values are
parameterized; all identifiers use psycopg.sql composition.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

import psycopg
from psycopg import sql

from hgnc_xref_loader.repositories.xref_staging_repository import (
    RowCountMismatchError,
    StagingPromotionError,
    XrefStagingRepository,
)

logger = logging.getLogger(__name__)


class PostgresXrefStagingRepository(XrefStagingRepository):
    """Postgres-backed xref staging repository using psycopg v3.

    Uses COPY for bulk loads, psycopg.sql for safe identifier composition,
    and transactional DDL for atomic staging-to-production promotion.

    Args:
        engine: SQLAlchemy engine configured with psycopg v3 driver.
            Must have pool_pre_ping and pool_recycle configured for
            Cloud Run resilience.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def health_check(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(sql.SQL("SELECT 1"))
            return True
        except Exception:
            return False

    def prepare_staging_table(self, source_table: str) -> str:
        staging_name = f"{source_table}_update"
        staging_id = sql.Identifier(staging_name)

        drop_stmt = sql.SQL("DROP TABLE IF EXISTS {table}").format(table=staging_id)
        create_stmt = sql.SQL(
            "CREATE TABLE {table} (LIKE {source} INCLUDING DEFAULTS)"
        ).format(
            table=staging_id,
            source=sql.Identifier(source_table),
        )

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(drop_stmt)
                cur.execute(create_stmt)

        logger.info(
            "staging_prepared",
            extra={"source_table": source_table, "staging_table": staging_name},
        )
        return staging_name

    def bulk_copy_into_staging(self, staging_table: str, records: list[dict]) -> int:
        if not records:
            logger.info(
                "bulk_copy_empty",
                extra={"staging_table": staging_table, "row_count": 0},
            )
            return 0

        columns = list(records[0].keys())
        col_ids = [sql.Identifier(c) for c in columns]
        copy_sql = sql.SQL("COPY {table} ({cols}) FROM STDIN WITH CSV HEADER").format(
            table=sql.Identifier(staging_table),
            cols=sql.SQL(", ").join(col_ids),
        )

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
        buf.seek(0)

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                with cur.copy(copy_sql) as copy:
                    copy.write(buf.read())

        count = len(records)
        logger.info(
            "bulk_copy_complete",
            extra={"staging_table": staging_table, "row_count": count},
        )
        return count

    def create_staging_indexes(self, staging_table: str, source_table: str) -> None:
        staging_id = sql.Identifier(staging_table)
        idx_name = sql.Identifier(f"idx_{staging_table}_hgnc_id")

        create_idx = sql.SQL(
            "CREATE INDEX IF NOT EXISTS {idx} ON {table} (hgnc_id)"
        ).format(idx=idx_name, table=staging_id)

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(create_idx)

        logger.info(
            "staging_indexes_created",
            extra={"staging_table": staging_table},
        )

    def validate_staging_row_count(
        self,
        staging_table: str,
        expected_count: int,
    ) -> None:
        count_stmt = sql.SQL("SELECT COUNT(*) FROM {table}").format(
            table=sql.Identifier(staging_table),
        )

        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(count_stmt)
                row = cur.fetchone()

        actual = row[0] if row else 0
        if actual != expected_count:
            raise RowCountMismatchError(
                staging_table=staging_table,
                expected=expected_count,
                actual=actual,
            )

        logger.info(
            "row_count_validated",
            extra={
                "staging_table": staging_table,
                "expected": expected_count,
                "actual": actual,
            },
        )

    def promote_staging_to_production(
        self,
        staging_table: str,
        source_table: str,
    ) -> None:
        drop_prod = sql.SQL("DROP TABLE IF EXISTS {table}").format(
            table=sql.Identifier(source_table),
        )
        rename = sql.SQL("ALTER TABLE {staging} RENAME TO {prod}").format(
            staging=sql.Identifier(staging_table),
            prod=sql.Identifier(source_table),
        )
        update_mod_dates = sql.SQL(
            "UPDATE table_mod_dates SET date_modified = NOW() WHERE table_name = %s"
        )

        try:
            with self._engine.raw_connection() as raw_conn:
                with raw_conn.cursor() as cur:
                    cur.execute(drop_prod)
                    cur.execute(rename)
                    cur.execute(update_mod_dates, [source_table])
                raw_conn.commit()

            logger.info(
                "promotion_complete",
                extra={
                    "staging_table": staging_table,
                    "source_table": source_table,
                },
            )
        except Exception as exc:
            raise StagingPromotionError(
                staging_table=staging_table,
                source_table=source_table,
            ) from exc
