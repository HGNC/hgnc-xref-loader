"""Tests for PostgresCcdsPostLoadRepository.

Validates the SQL-based CCDS post-load operations using mocked
SQLAlchemy sessions. Tests verify correct query patterns, parameter
binding, and error handling matching the Perl CCDS loader module.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, call

import pytest

sys.modules.setdefault("shared", MagicMock())
sys.modules.setdefault("shared.genew4_lock", MagicMock())
sys.modules.setdefault("shared.genew4_lock_error", MagicMock())

from hgnc_xref_loader.exceptions import RepositoryError
from hgnc_xref_loader.repositories.postgres_ccds_post_load_repository import (
    PostgresCcdsPostLoadRepository,
)


def _make_repo() -> tuple[PostgresCcdsPostLoadRepository, MagicMock]:
    session = MagicMock()
    repo = PostgresCcdsPostLoadRepository(session=session)
    return repo, session


class TestUpdateCcdsHgncIds:
    """Test update_ccds_hgnc_ids query execution."""

    def test_executes_update_joining_gene_on_eg_id(self) -> None:
        repo, session = _make_repo()
        repo.update_ccds_hgnc_ids()
        session.execute.assert_called()
        session.flush.assert_called()

    def test_raises_repository_error_on_failure(self) -> None:
        repo, session = _make_repo()
        session.execute.side_effect = RuntimeError("connection lost")
        with pytest.raises(RepositoryError, match="update CCDS hgnc_ids"):
            repo.update_ccds_hgnc_ids()


class TestAggregateCcdsIdsIntoGenes:
    """Test aggregate_ccds_ids_into_genes query execution."""

    def test_queries_and_updates_per_hgnc_id(self) -> None:
        repo, session = _make_repo()
        mock_agg_result = MagicMock()
        mock_agg_result.__iter__ = MagicMock(
            return_value=iter([(1, "CCDS1, CCDS2"), (2, "CCDS3")])
        )
        mock_update_result = MagicMock()
        session.execute.side_effect = [mock_agg_result, mock_update_result, mock_update_result]

        repo.aggregate_ccds_ids_into_genes(lock_code="test_lock")

        assert session.execute.call_count == 3

    def test_raises_repository_error_on_failure(self) -> None:
        repo, session = _make_repo()
        session.execute.side_effect = RuntimeError("db error")
        with pytest.raises(RepositoryError, match="aggregate CCDS IDs"):
            repo.aggregate_ccds_ids_into_genes(lock_code="test_lock")

    def test_skips_null_hgnc_id_rows(self) -> None:
        repo, session = _make_repo()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([(None, "CCDS1"), (2, "CCDS2")])
        )
        session.execute.side_effect = [mock_result, MagicMock()]

        repo.aggregate_ccds_ids_into_genes(lock_code="test_lock")

        assert session.execute.call_count == 2


class TestRebuildHgncId2ccdsId:
    """Test rebuild_hgnc_id2ccds_id bridge table maintenance."""

    def test_deletes_then_inserts(self) -> None:
        repo, session = _make_repo()
        repo.rebuild_hgnc_id2ccds_id()

        assert session.execute.call_count == 2
        session.flush.assert_called_once()

    def test_raises_repository_error_on_failure(self) -> None:
        repo, session = _make_repo()
        session.execute.side_effect = RuntimeError("db error")
        with pytest.raises(RepositoryError, match="rebuild hgnc_id2ccds_id"):
            repo.rebuild_hgnc_id2ccds_id()


class TestFindWithdrawnCcdsInGenes:
    """Test find_withdrawn_ccds_in_genes query."""

    def test_returns_list_of_dicts(self) -> None:
        repo, session = _make_repo()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([(100, "CCDS1.1", "Withdrawn")])
        )
        session.execute.return_value = mock_result

        result = repo.find_withdrawn_ccds_in_genes()

        assert len(result) == 1
        assert result[0] == {"hgnc_id": 100, "ccds_id": "CCDS1.1", "status": "Withdrawn"}

    def test_returns_empty_for_no_withdrawn(self) -> None:
        repo, session = _make_repo()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        session.execute.return_value = mock_result

        result = repo.find_withdrawn_ccds_in_genes()

        assert result == []

    def test_raises_repository_error_on_failure(self) -> None:
        repo, session = _make_repo()
        session.execute.side_effect = RuntimeError("db error")
        with pytest.raises(RepositoryError, match="find withdrawn CCDS"):
            repo.find_withdrawn_ccds_in_genes()


class TestRemoveCcdsFromGene:
    """Test remove_ccds_from_gene mutation."""

    def test_executes_update_with_correct_params(self) -> None:
        repo, session = _make_repo()
        repo.remove_ccds_from_gene(
            hgnc_id=100, ccds_id="CCDS1.1", status="Withdrawn", lock_code="lock123"
        )
        session.execute.assert_called_once()
        session.flush.assert_called_once()

        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["hgnc_id"] == 100
        assert params["ccds_id_pattern"] == "CCDS1.1"
        assert params["lock_code"] == "lock123"
        assert "Deleted CCDS1.1" in params["memo"]

    def test_raises_repository_error_on_failure(self) -> None:
        repo, session = _make_repo()
        session.execute.side_effect = RuntimeError("db error")
        with pytest.raises(RepositoryError, match="remove CCDS"):
            repo.remove_ccds_from_gene(
                hgnc_id=100, ccds_id="CCDS1.1", status="Withdrawn", lock_code="lock"
            )
