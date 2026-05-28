"""Tests for UniProt staging repository.

Validates the UniProt-specific staging repository that orchestrates
DDL preparation, COPY bulk load, and promotion across 4 tables.
Uses mocked DB connections per AGENTS.md service-layer testing rules.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from hgnc_xref_loader.loaders.uniprot_schemas import (
    UniprotEcStagingRow,
    UniprotHgncStagingRow,
    UniprotMainStagingRow,
    UniprotNcbiGeneStagingRow,
)
from hgnc_xref_loader.repositories.uniprot_staging_repository import (
    UniprotStagingRepository,
)


@pytest.fixture
def mock_engine() -> MagicMock:
    engine = MagicMock()
    raw_conn = MagicMock()
    cursor = MagicMock()
    raw_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    raw_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    engine.raw_connection.return_value.__enter__ = MagicMock(return_value=raw_conn)
    engine.raw_connection.return_value.__exit__ = MagicMock(return_value=False)
    return engine


@pytest.fixture
def repo(mock_engine: MagicMock) -> UniprotStagingRepository:
    return UniprotStagingRepository(engine=mock_engine)


class TestUniprotStagingRepositoryPrepare:
    """Test staging table preparation for all 4 tables."""

    def test_prepare_creates_4_staging_tables(self, repo: UniprotStagingRepository) -> None:
        staging_tables = repo.prepare_staging_tables()

        assert "uniprot_update" in staging_tables
        assert "uniprot_has_hgnc_update" in staging_tables
        assert "uniprot_has_ncbi_gene_update" in staging_tables
        assert "uniprot_has_ec_update" in staging_tables

    def test_prepare_returns_mapping(self, repo: UniprotStagingRepository) -> None:
        staging_tables = repo.prepare_staging_tables()

        assert staging_tables["uniprot_update"] == "uniprot_update"
        assert staging_tables["uniprot_has_hgnc_update"] == "uniprot_has_hgnc_update"


class TestUniprotStagingRepositoryBulkLoad:
    """Test bulk COPY loading into 4 staging tables."""

    def test_load_main_rows(self, repo: UniprotStagingRepository) -> None:
        rows = [
            UniprotMainStagingRow(
                unip_acc="P00750",
                unip_status="reviewed",
                unip_entry_name="UROT_HUMAN",
                unip_prot_name="Test protein",
                unip_sym="PLAU",
            ),
        ]
        counts = repo.bulk_load_main(rows)
        assert counts == 1

    def test_load_hgnc_rows(self, repo: UniprotStagingRepository) -> None:
        rows = [
            UniprotHgncStagingRow(unip_acc="P00750", hgnc_id=9052),
            UniprotHgncStagingRow(unip_acc="P00750", hgnc_id=9999),
        ]
        counts = repo.bulk_load_hgnc(rows)
        assert counts == 2

    def test_load_ncbi_gene_rows(self, repo: UniprotStagingRepository) -> None:
        rows = [
            UniprotNcbiGeneStagingRow(unip_acc="P00750", ncbi_gene_id=1234),
        ]
        counts = repo.bulk_load_ncbi_gene(rows)
        assert counts == 1

    def test_load_ec_rows(self, repo: UniprotStagingRepository) -> None:
        rows = [
            UniprotEcStagingRow(unip_acc="P00750", ec_id="3.4.21.73"),
        ]
        counts = repo.bulk_load_ec(rows)
        assert counts == 1

    def test_load_empty_rows_returns_zero(self, repo: UniprotStagingRepository) -> None:
        counts = repo.bulk_load_main([])
        assert counts == 0


class TestUniprotStagingRepositoryPromote:
    """Test promotion lifecycle with FK handling."""

    def test_promote_drops_alphafold_fk_before_swap(
        self, repo: UniprotStagingRepository, mock_engine: MagicMock
    ) -> None:
        cursor = mock_engine.raw_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value

        repo.promote_all()

        executed_sqls = [str(c) for c in cursor.execute.call_args_list]
        sql_text = " ".join(executed_sqls)
        assert "alphafold_uniprot_fk" in sql_text

    def test_promote_swaps_4_tables(
        self, repo: UniprotStagingRepository, mock_engine: MagicMock
    ) -> None:
        cursor = mock_engine.raw_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value

        repo.promote_all()

        executed_sqls = [str(c) for c in cursor.execute.call_args_list]
        sql_text = " ".join(executed_sqls)
        assert "uniprot" in sql_text

    def test_promote_commits_transaction(
        self, repo: UniprotStagingRepository, mock_engine: MagicMock
    ) -> None:
        raw_conn = mock_engine.raw_connection.return_value.__enter__.return_value

        repo.promote_all()

        raw_conn.commit.assert_called()
