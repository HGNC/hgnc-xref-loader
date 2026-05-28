"""UniProt-specific staging repository for 4-table bulk load and promotion.

Orchestrates DDL preparation, psycopg v3 COPY bulk load, and atomic
promotion across the four UniProt staging tables: ``uniprot_update``,
``uniprot_has_hgnc_update``, ``uniprot_has_ncbi_gene_update``, and
``uniprot_has_ec_update``.

DDL is strictly scoped to the loader exception (AGENTS.md Section 1.1):
DROP/CREATE on ``*_update`` staging tables, ALTER TABLE RENAME for
promotion, and index creation after swap.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from psycopg import sql

from hgnc_xref_loader.loaders.uniprot_schemas import (
    UniprotEcStagingRow,
    UniprotHasEcSchema,
    UniprotHasHgncSchema,
    UniprotHasNcbiGeneSchema,
    UniprotMainSchema,
    UniprotMainStagingRow,
    UniprotHgncStagingRow,
    UniprotNcbiGeneStagingRow,
)

logger = logging.getLogger(__name__)

TABLES = ["uniprot", "uniprot_has_hgnc", "uniprot_has_ncbi_gene", "uniprot_has_ec"]


class UniprotStagingRepository:
    """UniProt staging repository managing 4-table lifecycle.

    Handles DDL preparation (DROP/CREATE ``*_update`` staging tables),
    COPY bulk loading, and atomic promotion with alphafold FK handling.

    Args:
        engine: SQLAlchemy engine with psycopg v3 driver.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def prepare_staging_tables(self) -> dict[str, str]:
        """Create the four ``*_update`` staging tables.

        Returns:
            Mapping of staging table name to staging table name
            (for interface consistency).
        """
        staging_ddl = {
            UniprotMainSchema.staging_table: (
                "CREATE TABLE {table} ("
                "  unip_acc varchar,"
                "  unip_status varchar,"
                "  unip_entry_name varchar,"
                "  unip_prot_name text,"
                "  unip_sym varchar"
                ") WITH (OIDS=FALSE)"
            ),
            UniprotHasHgncSchema.staging_table: (
                "CREATE TABLE {table} ("
                "  unip_acc varchar NOT NULL,"
                "  hgnc_id int4 NOT NULL"
                ") WITH (OIDS=FALSE)"
            ),
            UniprotHasNcbiGeneSchema.staging_table: (
                "CREATE TABLE {table} ("
                "  unip_acc varchar NOT NULL,"
                "  ncbi_gene_id int4 NOT NULL"
                ") WITH (OIDS=FALSE)"
            ),
            UniprotHasEcSchema.staging_table: (
                "CREATE TABLE {table} ("
                "  unip_acc varchar NOT NULL,"
                "  ec_id varchar NOT NULL"
                ") WITH (OIDS=FALSE)"
            ),
        }

        result: dict[str, str] = {}
        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                for staging_name, ddl_template in staging_ddl.items():
                    staging_id = sql.Identifier(staging_name)
                    cur.execute(
                        sql.SQL("DROP TABLE IF EXISTS {table}").format(
                            table=staging_id
                        )
                    )
                    cur.execute(
                        sql.SQL(ddl_template).format(table=staging_id)
                    )
                    result[staging_name] = staging_name

        logger.info(
            "uniprot_staging_prepared",
            extra={"tables": list(result.keys())},
        )
        return result

    def bulk_load_main(self, rows: list[UniprotMainStagingRow]) -> int:
        """Bulk COPY main UniProt rows into ``uniprot_update``.

        Args:
            rows: Parsed main staging rows.

        Returns:
            Number of rows loaded.
        """
        return self._copy_rows(
            UniprotMainSchema.staging_table,
            list(UniprotMainSchema.columns),
            [r.to_dict() for r in rows],
        )

    def bulk_load_hgnc(self, rows: list[UniprotHgncStagingRow]) -> int:
        """Bulk COPY HGNC junction rows into ``uniprot_has_hgnc_update``.

        Args:
            rows: Parsed HGNC junction staging rows.

        Returns:
            Number of rows loaded.
        """
        return self._copy_rows(
            UniprotHasHgncSchema.staging_table,
            list(UniprotHasHgncSchema.columns),
            [r.to_dict() for r in rows],
        )

    def bulk_load_ncbi_gene(self, rows: list[UniprotNcbiGeneStagingRow]) -> int:
        """Bulk COPY NCBI Gene junction rows into ``uniprot_has_ncbi_gene_update``.

        Args:
            rows: Parsed NCBI Gene junction staging rows.

        Returns:
            Number of rows loaded.
        """
        return self._copy_rows(
            UniprotHasNcbiGeneSchema.staging_table,
            list(UniprotHasNcbiGeneSchema.columns),
            [r.to_dict() for r in rows],
        )

    def bulk_load_ec(self, rows: list[UniprotEcStagingRow]) -> int:
        """Bulk COPY EC junction rows into ``uniprot_has_ec_update``.

        Args:
            rows: Parsed EC junction staging rows.

        Returns:
            Number of rows loaded.
        """
        return self._copy_rows(
            UniprotHasEcSchema.staging_table,
            list(UniprotHasEcSchema.columns),
            [r.to_dict() for r in rows],
        )

    def promote_all(self) -> None:
        """Atomically promote all 4 staging tables to production.

        Drops the ``alphafold_uniprot_fk`` foreign key constraint before
        swapping ``uniprot``, then swaps all 4 tables and recreates indexes.
        """
        with self._engine.raw_connection() as raw_conn:
            with raw_conn.cursor() as cur:
                cur.execute(
                    sql.SQL(
                        "ALTER TABLE IF EXISTS alphafold "
                        "DROP CONSTRAINT IF EXISTS alphafold_uniprot_fk"
                    )
                )

                for table in TABLES:
                    staging = f"{table}_update"
                    cur.execute(
                        sql.SQL("DROP TABLE IF EXISTS {prod}").format(
                            prod=sql.Identifier(table)
                        )
                    )
                    cur.execute(
                        sql.SQL("ALTER TABLE {staging} RENAME TO {prod}").format(
                            staging=sql.Identifier(staging),
                            prod=sql.Identifier(table),
                        )
                    )

                self._create_indexes(cur)

            raw_conn.commit()

        logger.info("uniprot_promotion_complete", extra={"tables": TABLES})

    def _create_indexes(self, cur: Any) -> None:
        """Create indexes on the freshly promoted production tables.

        Args:
            cur: psycopg cursor within an active transaction.
        """
        cur.execute(
            sql.SQL(
                'ALTER TABLE "uniprot" ADD CONSTRAINT "uniprot_pkey" '
                'PRIMARY KEY ("unip_acc")'
            )
        )
        cur.execute(sql.SQL('DROP INDEX IF EXISTS "uniprot_status_idx"'))
        cur.execute(
            sql.SQL(
                'CREATE INDEX "uniprot_status_idx" ON "public"."uniprot" '
                "USING btree(unip_status ASC NULLS LAST)"
            )
        )

        cur.execute(sql.SQL('DROP INDEX IF EXISTS "uniprot_has_hgnc_hgnc_idx"'))
        cur.execute(
            sql.SQL(
                'CREATE INDEX "uniprot_has_hgnc_hgnc_idx" ON "public"."uniprot_has_hgnc" '
                "USING btree(hgnc_id ASC NULLS LAST)"
            )
        )
        cur.execute(sql.SQL('DROP INDEX IF EXISTS "uniprot_has_hgnc_uniprot_idx"'))
        cur.execute(
            sql.SQL(
                'CREATE INDEX "uniprot_has_hgnc_uniprot_idx" ON "public"."uniprot_has_hgnc" '
                "USING btree(unip_acc ASC NULLS LAST)"
            )
        )

        cur.execute(sql.SQL('DROP INDEX IF EXISTS "uniprot_has_ec_ec_idx"'))
        cur.execute(
            sql.SQL(
                'CREATE INDEX "uniprot_has_ec_ec_idx" ON "public"."uniprot_has_ec" '
                "USING btree(ec_id ASC NULLS LAST)"
            )
        )
        cur.execute(sql.SQL('DROP INDEX IF EXISTS "uniprot_has_ec_uniprot_idx"'))
        cur.execute(
            sql.SQL(
                'CREATE INDEX "uniprot_has_ec_uniprot_idx" ON "public"."uniprot_has_ec" '
                "USING btree(unip_acc ASC NULLS LAST)"
            )
        )

        cur.execute(
            sql.SQL(
                'DROP INDEX IF EXISTS "uniprot_has_ncbi_gene_ncbi_gene_id_idx"'
            )
        )
        cur.execute(
            sql.SQL(
                'CREATE INDEX "uniprot_has_ncbi_gene_ncbi_gene_id_idx" '
                'ON "public"."uniprot_has_ncbi_gene" '
                "USING btree(ncbi_gene_id ASC NULLS LAST)"
            )
        )
        cur.execute(
            sql.SQL('DROP INDEX IF EXISTS "uniprot_has_ncbi_gene_uniprot_idx"')
        )
        cur.execute(
            sql.SQL(
                'CREATE INDEX "uniprot_has_ncbi_gene_uniprot_idx" '
                'ON "public"."uniprot_has_ncbi_gene" '
                "USING btree(unip_acc ASC NULLS LAST)"
            )
        )

    def _copy_rows(
        self, staging_table: str, columns: list[str], records: list[dict]
    ) -> int:
        """Perform COPY bulk load into a staging table.

        Args:
            staging_table: Target staging table name.
            columns: Column names in order.
            records: Row dicts to load.

        Returns:
            Number of rows loaded.
        """
        if not records:
            return 0

        col_ids = [sql.Identifier(c) for c in columns]
        copy_sql = sql.SQL(
            "COPY {table} ({cols}) FROM STDIN WITH CSV HEADER"
        ).format(
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
            "uniprot_bulk_copy",
            extra={"staging_table": staging_table, "row_count": count},
        )
        return count
