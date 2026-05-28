"""Tests for CCDS post-load routines.

Validates the post-load steps: add_hgnc_ids (joining CCDS to Gene on NCBI
gene IDs, using Genew4Lock, updating ccds.hgnc_id, aggregating ccds_ids,
rebuilding junction) and remove_withdrawn_ccds (detecting withdrawn CCDS
IDs in gene.ccds_ids, removing them, appending audit notes to edit_memo).
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("shared", MagicMock())
sys.modules.setdefault("shared.genew4_lock", MagicMock())
sys.modules.setdefault("shared.genew4_lock_error", MagicMock())


class TestCcdsPostLoadServiceImports:
    """Verify the service can be imported."""

    def test_import_ccds_post_load_service(self) -> None:
        from hgnc_xref_loader.services.ccds_post_load_service import CcdsPostLoadService

        assert CcdsPostLoadService is not None


class TestAddHgncIds:
    """Verify the add_hgnc_ids post-load routine."""

    def _make_service(
        self,
        lock: MagicMock | None = None,
        post_load_repo: MagicMock | None = None,
    ) -> "CcdsPostLoadService":
        from hgnc_xref_loader.services.ccds_post_load_service import CcdsPostLoadService

        mock_lock = lock or MagicMock()
        mock_lock.lock_code = "test:_:host:_:123:_:1"
        mock_repo = post_load_repo or MagicMock()
        return CcdsPostLoadService(
            lock=mock_lock,
            post_load_repo=mock_repo,
        )

    def test_lock_all_called_before_mutations(self) -> None:
        svc = self._make_service()
        svc.add_hgnc_ids()
        svc._lock.lock_all.assert_called_once()

    def test_unlock_all_called_after_mutations(self) -> None:
        svc = self._make_service()
        svc.add_hgnc_ids()
        svc._lock.unlock_all.assert_called_once()

    def test_unlock_all_called_even_on_repo_error(self) -> None:
        svc = self._make_service()
        svc._post_load_repo.update_ccds_hgnc_ids.side_effect = RuntimeError("db error")
        with pytest.raises(RuntimeError, match="db error"):
            svc.add_hgnc_ids()
        svc._lock.unlock_all.assert_called_once()

    def test_update_ccds_hgnc_ids_called(self) -> None:
        svc = self._make_service()
        svc.add_hgnc_ids()
        svc._post_load_repo.update_ccds_hgnc_ids.assert_called_once()

    def test_aggregate_ccds_ids_called_with_lock_code(self) -> None:
        svc = self._make_service()
        svc.add_hgnc_ids()
        svc._post_load_repo.aggregate_ccds_ids_into_genes.assert_called_once_with(
            lock_code="test:_:host:_:123:_:1"
        )

    def test_rebuild_junction_table_called(self) -> None:
        svc = self._make_service()
        svc.add_hgnc_ids()
        svc._post_load_repo.rebuild_hgnc_id2ccds_id.assert_called_once()

    def test_full_lifecycle_order(self) -> None:
        svc = self._make_service()
        call_order: list[str] = []

        svc._lock.lock_all.side_effect = lambda: call_order.append("lock_all")
        svc._post_load_repo.update_ccds_hgnc_ids.side_effect = lambda: call_order.append(
            "update_hgnc_ids"
        )
        svc._post_load_repo.aggregate_ccds_ids_into_genes.side_effect = (
            lambda lock_code: call_order.append("aggregate")
        )
        svc._post_load_repo.rebuild_hgnc_id2ccds_id.side_effect = lambda: call_order.append(
            "rebuild"
        )
        svc._lock.unlock_all.side_effect = lambda: call_order.append("unlock_all")

        svc.add_hgnc_ids()

        assert call_order == [
            "lock_all",
            "update_hgnc_ids",
            "aggregate",
            "rebuild",
            "unlock_all",
        ]


class TestRemoveWithdrawnCcds:
    """Verify the remove_withdrawn_ccds cleanup routine."""

    def _make_service(
        self,
        lock: MagicMock | None = None,
        post_load_repo: MagicMock | None = None,
    ) -> "CcdsPostLoadService":
        from hgnc_xref_loader.services.ccds_post_load_service import CcdsPostLoadService
        mock_lock = lock or MagicMock()
        mock_lock.lock_code = "test:_:host:_:123:_:1"
        mock_repo = post_load_repo or MagicMock()
        return CcdsPostLoadService(
            lock=mock_lock,
            post_load_repo=mock_repo,
        )

    def test_find_withdrawn_called(self) -> None:
        svc = self._make_service()
        svc.remove_withdrawn_ccds()
        svc._post_load_repo.find_withdrawn_ccds_in_genes.assert_called_once()

    def test_remove_withdrawn_for_each_result(self) -> None:
        svc = self._make_service()
        withdrawn = [
            {"hgnc_id": 100, "ccds_id": "CCDS1.1", "status": "Withdrawn"},
            {"hgnc_id": 200, "ccds_id": "CCDS2.1", "status": "Withdrawn, under review"},
        ]
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = withdrawn
        svc.remove_withdrawn_ccds()
        assert svc._post_load_repo.remove_ccds_from_gene.call_count == 2

    def test_remove_ccds_from_gene_receives_correct_args(self) -> None:
        svc = self._make_service()
        withdrawn = [
            {"hgnc_id": 100, "ccds_id": "CCDS1.1", "status": "Withdrawn"},
        ]
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = withdrawn
        svc.remove_withdrawn_ccds()
        svc._post_load_repo.remove_ccds_from_gene.assert_called_once_with(
            hgnc_id=100,
            ccds_id="CCDS1.1",
            status="Withdrawn",
            lock_code="test:_:host:_:123:_:1",
        )

    def test_no_withdrawn_means_no_mutations(self) -> None:
        svc = self._make_service()
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = []
        svc.remove_withdrawn_ccds()
        svc._post_load_repo.remove_ccds_from_gene.assert_not_called()

    def test_unlock_all_called_after_withdrawn_cleanup(self) -> None:
        svc = self._make_service()
        svc.remove_withdrawn_ccds()
        svc._lock.unlock_all.assert_called_once()

    def test_unlock_called_even_on_remove_error(self) -> None:
        svc = self._make_service()
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = [
            {"hgnc_id": 100, "ccds_id": "CCDS1.1", "status": "Withdrawn"},
        ]
        svc._post_load_repo.remove_ccds_from_gene.side_effect = RuntimeError("db")
        with pytest.raises(RuntimeError, match="db"):
            svc.remove_withdrawn_ccds()
        svc._lock.unlock_all.assert_called_once()
