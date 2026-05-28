"""CCDS post-load service for add_hgnc_ids and remove_withdrawn_ccds.

Handles the post-staging-promotion mutations that join CCDS data to Gene
records, aggregate CCDS IDs, and rebuild junction tables. Uses Genew4Lock
for optimistic locking to prevent concurrent mutations.

Follows the Perl HGNC::DB::PostgreSQL::Genew4::Load::Table::CCDS module's
post-load lifecycle.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class CcdsPostLoadRepository(Protocol):
    """Protocol for CCDS post-load database operations.

    Defines the interface for repository methods that perform the
    CCDS-to-Gene joins and mutations during post-load processing.
    """

    def update_ccds_hgnc_ids(self) -> None:
        """Join ccds.ncbi_gene_id to gene.public_ncbi_gene_id and update ccds.hgnc_id."""
        ...

    def aggregate_ccds_ids_into_genes(self, lock_code: str) -> None:
        """Aggregate ccds_id into gene.ccds_ids for Public status genes.

        Args:
            lock_code: Genew4Lock code for safe row updates.
        """
        ...

    def rebuild_hgnc_id2ccds_id(self) -> None:
        """Rebuild the HgncId2CcdsId junction table from Public CCDS records."""
        ...

    def find_withdrawn_ccds_in_genes(self) -> list[dict[str, Any]]:
        """Find withdrawn CCDS IDs still present in gene.ccds_ids.

        Returns:
            List of dicts with keys: hgnc_id, ccds_id, status.
        """
        ...

    def remove_ccds_from_gene(
        self, hgnc_id: int, ccds_id: str, status: str, lock_code: str
    ) -> None:
        """Remove a CCDS ID from gene.ccds_ids and append audit note to edit_memo.

        Args:
            hgnc_id: Gene HGNC ID.
            ccds_id: CCDS ID to remove.
            status: Withdrawal status for the audit note.
            lock_code: Genew4Lock code for safe row updates.
        """
        ...


class CcdsPostLoadService:
    """Post-load service for CCDS add_hgnc_ids routine.

    Orchestrates the post-promotion mutations using Genew4Lock:
    1. Lock all Gene rows
    2. Join CCDS→Gene on NCBI gene ID and update ccds.hgnc_id
    3. Aggregate ccds_id into gene.ccds_ids
    4. Rebuild HgncId2CcdsId junction table
    5. Unlock all Gene rows (even on error)

    Args:
        lock: Genew4Lock instance for optimistic locking.
        post_load_repo: Repository for post-load database operations.
    """

    def __init__(self, lock: Any, post_load_repo: CcdsPostLoadRepository) -> None:
        self._lock = lock
        self._post_load_repo = post_load_repo

    def add_hgnc_ids(self) -> None:
        """Execute the add_hgnc_ids post-load routine.

        Locks all Gene rows, updates CCDS HGNC IDs, aggregates CCDS IDs
        into Gene records, and rebuilds the junction table. Unlocks
        unconditionally in a finally block.

        Raises:
            Exception: Propagates any database or lock errors after unlocking.
        """
        self._lock.lock_all()
        try:
            self._post_load_repo.update_ccds_hgnc_ids()
            self._post_load_repo.aggregate_ccds_ids_into_genes(
                lock_code=self._lock.lock_code
            )
            self._post_load_repo.rebuild_hgnc_id2ccds_id()
        finally:
            self._lock.unlock_all()

    def remove_withdrawn_ccds(self) -> None:
        """Remove withdrawn CCDS IDs from gene.ccds_ids and audit via edit_memo.

        Finds CCDS IDs with Withdrawn status that still appear in gene.ccds_ids,
        removes them from the comma-separated string, and appends an audit note.
        Unlocks unconditionally in a finally block.

        Raises:
            Exception: Propagates any database or lock errors after unlocking.
        """
        self._lock.lock_all()
        try:
            withdrawn = self._post_load_repo.find_withdrawn_ccds_in_genes()
            for entry in withdrawn:
                self._post_load_repo.remove_ccds_from_gene(
                    hgnc_id=entry["hgnc_id"],
                    ccds_id=entry["ccds_id"],
                    status=entry["status"],
                    lock_code=self._lock.lock_code,
                )
        finally:
            self._lock.unlock_all()
