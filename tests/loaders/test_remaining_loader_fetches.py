"""Tests for remaining loader fetch_and_parse implementations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hgnc_xref_loader.loaders.individual_loaders import (
    Ensembl2HgncCompleteLoader,
    EnsemblGeneLoader,
    EnsemblSeqLoader,
    ImgtLoader,
    LovdLoader,
)


def test_ensembl_gene_loader_uses_repository() -> None:
    with patch("ensembl_orm.session.get_session", return_value=MagicMock()):
        with patch(
            "hgnc_xref_loader.repositories.ensembl_gene_repository.EnsemblGeneRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.fetch_genes.return_value = [{"gene_id": "ENSG1"}]
            mock_repo_cls.return_value = mock_repo

            loader = EnsemblGeneLoader()
            rows = loader.fetch_and_parse()

    assert rows == [{"gene_id": "ENSG1"}]


def test_ensembl2hgnc_complete_loader_uses_repository() -> None:
    with patch("ensembl_orm.session.get_session", return_value=MagicMock()):
        with patch(
            "hgnc_xref_loader.repositories.ensembl2hgnc_complete_repository.Ensembl2HgncCompleteRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.fetch_all_mappings.return_value = [{"e2ha_hgnc_id": 5}]
            mock_repo_cls.return_value = mock_repo

            loader = Ensembl2HgncCompleteLoader()
            rows = loader.fetch_and_parse()

    assert rows == [{"e2ha_hgnc_id": 5}]


def test_ensembl_seq_loader_fetches_cdna_and_ncrna() -> None:
    fetch_client = MagicMock()
    fetch_client.fetch.side_effect = [b"cdna", b"ncrna"]

    with patch(
        "hgnc_xref_loader.loaders.ensembl_seq_parser.EnsemblSeqParser.parse_cdna"
    ) as mock_cdna:
        with patch(
            "hgnc_xref_loader.loaders.ensembl_seq_parser.EnsemblSeqParser.parse_ncrna"
        ) as mock_ncrna:
            cdna_rec = MagicMock()
            cdna_rec.to_staging_dict.return_value = {"eseq_source": "cdna"}
            ncrna_rec = MagicMock()
            ncrna_rec.to_staging_dict.return_value = {"eseq_source": "ncrna"}
            mock_cdna.return_value = [cdna_rec]
            mock_ncrna.return_value = [ncrna_rec]

            loader = EnsemblSeqLoader(fetch_client=fetch_client)
            rows = loader.fetch_and_parse()

    assert fetch_client.fetch.call_count == 2
    assert rows == [{"eseq_source": "cdna"}, {"eseq_source": "ncrna"}]


def test_lovd_loader_parses_multi_gene_rows() -> None:
    line = '\t'.join(["x"] * 6 + ["LovdDB", "http://lovd.test", "GENE1, GENE2"]) + "\n"
    data = ("header\n" + line).encode("utf-8")
    fetch_client = MagicMock()
    fetch_client.fetch.return_value = data

    loader = LovdLoader(fetch_client=fetch_client)
    rows = loader.fetch_and_parse()

    assert len(rows) == 2
    assert rows[0]["lovd_db_genes"] == "GENE1"
    assert rows[1]["lovd_db_genes"] == "GENE2"


def test_imgt_loader_parses_pre_block() -> None:
    row = "species;id;fn;name;alleles;chrom;acc;sym;5;123;vega;atlas;cards;P12345"
    html = f"<html><pre>header\n{row}\n</pre></html>".encode("utf-8")
    fetch_client = MagicMock()
    fetch_client.fetch.return_value = html

    loader = ImgtLoader(fetch_client=fetch_client)
    rows = loader.fetch_and_parse()

    assert len(rows) == 1
    assert rows[0]["im_hgnc_id"] == "5"
    assert rows[0]["im_uniprot"] == "P12345"
