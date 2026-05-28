"""Tests for CCDS idempotency and transactional boundary guarantees.

Validates that re-running post-load routines is safe and that locking
guarantees hold under error conditions.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, call

import pytest

sys.modules.setdefault("shared", MagicMock())
sys.modules.setdefault("shared.genew4_lock", MagicMock())
sys.modules.setdefault("shared.genew4_lock_error", MagicMock())


def _make_service(
    lock: MagicMock | None = None,
    post_load_repo: MagicMock | None = None,
) -> "CcdsPostLoadService":
    from hgnc_xref_loader.services.ccds_post_load_service import CcdsPostLoadService

    mock_lock = lock or MagicMock()
    mock_lock.lock_code = "test:_:host:_:123:_:1"
    mock_repo = post_load_repo or MagicMock()
    return CcdsPostLoadService(lock=mock_lock, post_load_repo=mock_repo)


class TestIdempotency:
    """Verify that repeated invocations produce safe results."""

    def test_add_hgnc_ids_idempotent_on_repeated_call(self) -> None:
        svc = _make_service()
        svc.add_hgnc_ids()
        svc.add_hgnc_ids()
        assert svc._post_load_repo.update_ccds_hgnc_ids.call_count == 2
        assert svc._lock.lock_all.call_count == 2
        assert svc._lock.unlock_all.call_count == 2

    def test_remove_withdrawn_idempotent_no_withdrawn(self) -> None:
        svc = _make_service()
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = []
        svc.remove_withdrawn_ccds()
        svc.remove_withdrawn_ccds()
        assert svc._post_load_repo.remove_ccds_from_gene.call_count == 0

    def test_remove_withdrawn_only_processes_current_withdrawn(self) -> None:
        svc = _make_service()
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = [
            {"hgnc_id": 100, "ccds_id": "CCDS1.1", "status": "Withdrawn"},
        ]
        svc.remove_withdrawn_ccds()
        assert svc._post_load_repo.remove_ccds_from_gene.call_count == 1

        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = []
        svc.remove_withdrawn_ccds()
        total = svc._post_load_repo.remove_ccds_from_gene.call_count
        assert total == 1


class TestLockingGuarantees:
    """Verify lock/unlock ordering under various conditions."""

    def test_lock_all_precedes_all_mutations(self) -> None:
        svc = _make_service()
        call_order: list[str] = []

        svc._lock.lock_all.side_effect = lambda: call_order.append("lock")
        svc._post_load_repo.update_ccds_hgnc_ids.side_effect = lambda: call_order.append(
            "update"
        )
        svc._lock.unlock_all.side_effect = lambda: call_order.append("unlock")

        svc.add_hgnc_ids()
        lock_idx = call_order.index("lock")
        update_idx = call_order.index("update")
        unlock_idx = call_order.index("unlock")
        assert lock_idx < update_idx < unlock_idx

    def test_remove_withdrawn_unlock_on_empty_results(self) -> None:
        svc = _make_service()
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = []
        svc.remove_withdrawn_ccds()
        svc._lock.unlock_all.assert_called_once()

    def test_add_hgnc_ids_unlock_on_rebuild_error(self) -> None:
        svc = _make_service()
        svc._post_load_repo.rebuild_hgnc_id2ccds_id.side_effect = RuntimeError("junction")
        with pytest.raises(RuntimeError, match="junction"):
            svc.add_hgnc_ids()
        svc._lock.unlock_all.assert_called_once()

    def test_remove_withdrawn_unlock_after_partial_processing(self) -> None:
        svc = _make_service()
        svc._post_load_repo.find_withdrawn_ccds_in_genes.return_value = [
            {"hgnc_id": 100, "ccds_id": "CCDS1.1", "status": "Withdrawn"},
            {"hgnc_id": 200, "ccds_id": "CCDS2.1", "status": "Withdrawn"},
        ]
        svc._post_load_repo.remove_ccds_from_gene.side_effect = [
            None,
            RuntimeError("partial"),
        ]
        with pytest.raises(RuntimeError, match="partial"):
            svc.remove_withdrawn_ccds()
        assert svc._post_load_repo.remove_ccds_from_gene.call_count == 2
        svc._lock.unlock_all.assert_called_once()
