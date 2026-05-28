"""Tests for Ensembl2Hgnc MySQL fetch repository.

Validates the SQLAlchemy query construction for fetching Ensembl-to-HGNC
mappings from the Ensembl MySQL database via ensembl-orm.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from hgnc_xref_loader.repositories.ensembl2hgnc_repository import (
    Ensembl2HgncRecord,
    Ensembl2HgncRepository,
)


class TestEnsembl2HgncRecord:
    """Test the DTO for Ensembl2Hgnc rows."""

    def test_record_fields(self) -> None:
        rec = Ensembl2HgncRecord(
            hgnc_id="HGNC:9052",
            hgnc_symbol="PLAU",
            ensembl_gene_id="ENSG00000124383",
        )
        assert rec.hgnc_id == "HGNC:9052"
        assert rec.hgnc_symbol == "PLAU"
        assert rec.ensembl_gene_id == "ENSG00000124383"

    def test_record_to_dict(self) -> None:
        rec = Ensembl2HgncRecord(
            hgnc_id="HGNC:9052",
            hgnc_symbol="PLAU",
            ensembl_gene_id="ENSG00000124383",
        )
        d = rec.to_staging_dict()
        assert d == {
            "e2h_hgnc_id": "HGNC:9052",
            "e2h_app_sym": "PLAU",
            "e2h_ensembl_gene_id": "ENSG00000124383",
        }


class TestEnsembl2HgncRepositoryFetch:
    """Test the MySQL fetch with mocked session."""

    def test_fetch_returns_records(self) -> None:
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([
                ("HGNC:9052", "PLAU", "ENSG00000124383"),
            ])
        )
        mock_session.execute.return_value = mock_result

        repo = Ensembl2HgncRepository(session=mock_session)
        records = repo.fetch_mappings()

        assert len(records) == 1
        assert records[0].hgnc_id == "HGNC:9052"
        assert records[0].ensembl_gene_id == "ENSG00000124383"

    def test_fetch_excludes_lrg_prefix(self) -> None:
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([
                ("HGNC:9052", "PLAU", "ENSG00000124383"),
                ("HGNC:1234", "TEST", "LRG_123"),
            ])
        )
        mock_session.execute.return_value = mock_result

        repo = Ensembl2HgncRepository(session=mock_session)
        records = repo.fetch_mappings()

        assert len(records) == 1
        assert records[0].ensembl_gene_id == "ENSG00000124383"

    def test_fetch_calls_execute(self) -> None:
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_result

        repo = Ensembl2HgncRepository(session=mock_session)
        repo.fetch_mappings()

        mock_session.execute.assert_called_once()

    def test_fetch_multiple_records(self) -> None:
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([
                ("HGNC:9052", "PLAU", "ENSG00000124383"),
                ("HGNC:12853", "YWHAB", "ENSG00000166947"),
                ("HGNC:9999", "BRCA1", "ENSG00000012048"),
            ])
        )
        mock_session.execute.return_value = mock_result

        repo = Ensembl2HgncRepository(session=mock_session)
        records = repo.fetch_mappings()

        assert len(records) == 3


class TestEnsembl2HgncStagingSchema:
    """Test staging table schema definitions."""

    def test_staging_table_name(self) -> None:
        from hgnc_xref_loader.repositories.ensembl2hgnc_repository import (
            ENSEMBL2HGNC_STAGING_TABLE,
        )

        assert ENSEMBL2HGNC_STAGING_TABLE == "ensembl2hgnc_update"

    def test_staging_columns(self) -> None:
        from hgnc_xref_loader.repositories.ensembl2hgnc_repository import (
            ENSEMBL2HGNC_STAGING_COLUMNS,
        )

        assert ENSEMBL2HGNC_STAGING_COLUMNS == [
            "e2h_hgnc_id",
            "e2h_app_sym",
            "e2h_ensembl_gene_id",
        ]
