"""Tests for Ensembl loader fetch_and_parse implementation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hgnc_xref_loader.loaders.ensembl_loader import EnsemblXrefLoader


def test_fetch_and_parse_uses_repository_mappings() -> None:
    mock_record = MagicMock()
    mock_record.to_staging_dict.return_value = {
        "e2h_hgnc_id": "HGNC:5",
        "e2h_app_sym": "A1BG",
        "e2h_ensembl_gene_id": "ENSG00000121410",
    }

    mock_repo = MagicMock()
    mock_repo.fetch_mappings.return_value = [mock_record]

    with patch("ensembl_orm.session.get_session") as mock_get_session:
        with patch(
            "hgnc_xref_loader.repositories.ensembl2hgnc_repository.Ensembl2HgncRepository",
            return_value=mock_repo,
        ):
            loader = EnsemblXrefLoader()
            rows = loader.fetch_and_parse()

    mock_get_session.assert_called_once()
    mock_repo.fetch_mappings.assert_called_once()
    assert rows == [
        {
            "e2h_hgnc_id": "HGNC:5",
            "e2h_app_sym": "A1BG",
            "e2h_ensembl_gene_id": "ENSG00000121410",
        }
    ]
