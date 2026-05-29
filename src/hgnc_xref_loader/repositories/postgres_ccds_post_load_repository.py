"""Postgres repository for CCDS post-load gene column updates.

Implements the CcdsPostLoadRepository protocol using genew4-orm for
Gene model access and SQLAlchemy for queries. Handles:

1. update_ccds_hgnc_ids: Join ccds to gene on eg_id, set ccds.hgnc_id
2. aggregate_ccds_ids_into_genes: string_agg ccds_ids into gene.ccds_ids
3. rebuild_hgnc_id2ccds_id: DELETE + INSERT bridge table
4. find_withdrawn_ccds_in_genes: Find withdrawn CCDS still in gene.ccds_ids
5. remove_ccds_from_gene: Remove CCDS ID from gene, append audit memo
"""

from __future__ import annotations

import logging
from typing import Any

from genew4_orm import models as orm
from sqlalchemy import text, update, delete
from sqlalchemy.orm import Session

from hgnc_xref_loader.exceptions import RepositoryError

logger = logging.getLogger(__name__)


class PostgresCcdsPostLoadRepository:
    """Postgres implementation of CCDS post-load operations.

    Uses genew4-orm models (Gene, Ccds, HgncId2CcdsId) for all queries.
    Raw SQL is used only for complex aggregation that the ORM cannot
    express cleanly.

    Args:
        session: SQLAlchemy read-write session for mutations.
    """

    def __init__(self, session: Session) -> None:
        """Initialise with a read-write session.

        Args:
            session: SQLAlchemy Session for executing mutations.
        """
        self._session = session

    def update_ccds_hgnc_ids(self) -> None:
        """Join ccds to gene on eg_id and set ccds.hgnc_id.

        Matches the Perl add_hgnc_ids first step: update the ccds
        table's hgnc_id column by joining to gene on NCBI gene ID.
        Only considers genes with status='Approved'.

        Raises:
            RepositoryError: On database failure.
        """
        try:
            stmt = text("""
                UPDATE ccds
                SET ccds_hgnc_id = gene.hgnc_id
                FROM gene
                WHERE gene.hgnc_pub_eg_id::varchar = ccds.ccds_eg_id
                  AND gene.hgnc_status = 'Approved'
                  AND ccds.ccds_hgnc_id IS DISTINCT FROM gene.hgnc_id
            """)
            self._session.execute(stmt)
            self._session.flush()
            logger.info("ccds_hgnc_ids_updated")
        except Exception as exc:
            raise RepositoryError(
                f"Failed to update CCDS hgnc_ids: {exc}"
            ) from exc

    def aggregate_ccds_ids_into_genes(self, lock_code: str) -> None:
        """Aggregate Public ccds_ids into gene.ccds_ids per hgnc_id.

        Matches the Perl add_hgnc_ids second step: compute string_agg
        of distinct ccds_id where status='Public' grouped by ccds_hgnc_id,
        and update gene.ccds_ids for each locked gene row.

        Args:
            lock_code: Genew4Lock code to verify locked rows.

        Raises:
            RepositoryError: On database failure.
        """
        try:
            agg_stmt = text("""
                SELECT ccds_hgnc_id, string_agg(DISTINCT ccds_id, ', ') AS ccds_ids
                FROM ccds
                WHERE ccds_status = 'Public'
                  AND ccds_hgnc_id IS NOT NULL
                GROUP BY ccds_hgnc_id
            """)
            results = self._session.execute(agg_stmt)

            for row in results:
                if row[0] is None:
                    continue
                update_stmt = (
                    update(orm.Gene)
                    .where(
                        orm.Gene.lock == lock_code,
                        orm.Gene.hgnc_id == row[0],
                    )
                    .values(ccds_ids=row[1])
                )
                self._session.execute(update_stmt)

            self._session.flush()
            logger.info("ccds_ids_aggregated_into_genes")
        except Exception as exc:
            raise RepositoryError(
                f"Failed to aggregate CCDS IDs into genes: {exc}"
            ) from exc

    def rebuild_hgnc_id2ccds_id(self) -> None:
        """Rebuild the hgnc_id2ccds_id bridge table from Public CCDS records.

        Matches the Perl add_hgnc_ids third step: delete all rows from
        hgnc_id2ccds_id, then insert from ccds where status='Public'
        and hgnc_id is set.

        Raises:
            RepositoryError: On database failure.
        """
        try:
            self._session.execute(delete(orm.HgncId2CcdsId))

            insert_stmt = text("""
                INSERT INTO hgnc_id2ccds_id (hgnc_id2ccds_id_hgnc_id, hgnc_id2ccds_id_ccds_id)
                SELECT ccds_hgnc_id, ccds_id
                FROM ccds
                WHERE ccds_status = 'Public'
                  AND ccds_hgnc_id IS NOT NULL
            """)
            self._session.execute(insert_stmt)
            self._session.flush()
            logger.info("hgnc_id2ccds_id_rebuilt")
        except Exception as exc:
            raise RepositoryError(
                f"Failed to rebuild hgnc_id2ccds_id: {exc}"
            ) from exc

    def find_withdrawn_ccds_in_genes(self) -> list[dict[str, Any]]:
        """Find withdrawn CCDS IDs still present in gene.ccds_ids.

        Matches the Perl remove_withdrawn_ccds query. Excludes
        'Reviewed, withdrawal pending' status.

        Returns:
            List of dicts with hgnc_id, ccds_id, and status keys.

        Raises:
            RepositoryError: On database failure.
        """
        try:
            stmt = text("""
                SELECT ccds.ccds_hgnc_id AS hgnc_id,
                       ccds.ccds_id,
                       ccds.ccds_status AS status
                FROM ccds, gene
                WHERE ccds.ccds_status ILIKE 'Withdrawn%%'
                  AND ccds.ccds_status != 'Reviewed, withdrawal pending'
                  AND ccds.ccds_hgnc_id IS NOT NULL
                  AND ccds.ccds_hgnc_id = gene.hgnc_id
                  AND string_to_array(gene.hgnc_ccds_ids, ', ') && ARRAY[CAST(ccds.ccds_id AS TEXT)]
            """)
            results = self._session.execute(stmt)
            return [
                {"hgnc_id": row[0], "ccds_id": row[1], "status": row[2]}
                for row in results
            ]
        except Exception as exc:
            raise RepositoryError(
                f"Failed to find withdrawn CCDS: {exc}"
            ) from exc

    def remove_ccds_from_gene(
        self, hgnc_id: int, ccds_id: str, status: str, lock_code: str
    ) -> None:
        """Remove a CCDS ID from gene.ccds_ids and append audit memo.

        Matches the Perl update_ccds method: uses regexp_replace to
        strip the CCDS ID and appends an audit note to edit_memo.

        Args:
            hgnc_id: Gene HGNC ID.
            ccds_id: CCDS ID to remove.
            status: Withdrawal status for the audit note.
            lock_code: Genew4Lock code for safe row updates.

        Raises:
            RepositoryError: On database failure.
        """
        try:
            memo = (
                f"Deleted {ccds_id} from record as CCDS status is now \"{status}\""
            )
            stmt = text("""
                UPDATE gene
                SET hgnc_ccds_ids = regexp_replace(hgnc_ccds_ids, :ccds_id_pattern, ''),
                    hgnc_edit_memo = COALESCE(hgnc_edit_memo, '') || E'\\n' || :memo
                WHERE hgnc_lock = :lock_code
                  AND hgnc_id = :hgnc_id
            """)
            self._session.execute(
                stmt,
                {
                    "ccds_id_pattern": ccds_id,
                    "memo": memo,
                    "lock_code": lock_code,
                    "hgnc_id": hgnc_id,
                },
            )
            self._session.flush()
            logger.info(
                "ccds_removed_from_gene",
                extra={"hgnc_id": hgnc_id, "ccds_id": ccds_id},
            )
        except Exception as exc:
            raise RepositoryError(
                f"Failed to remove CCDS {ccds_id} from gene {hgnc_id}: {exc}"
            ) from exc
