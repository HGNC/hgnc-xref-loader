"""Tests for remaining loader fetch_and_parse implementations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hgnc_xref_loader.loaders.individual_loaders import (
    CytobandLoader,
    Ensembl2HgncCompleteLoader,
    EnsemblGeneLoader,
    EnsemblSeqLoader,
    ImgtLoader,
    LovdLoader,
    Ucsc2HgncLoader,
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


def test_ensembl2hgnc_complete_loader_removes_conflicting_alt_loci_rows() -> None:
    with patch("ensembl_orm.session.get_session", return_value=MagicMock()):
        with patch(
            "hgnc_xref_loader.repositories.ensembl2hgnc_complete_repository.Ensembl2HgncCompleteRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.fetch_all_mappings.return_value = [
                {
                    "e2ha_hgnc_id": 5,
                    "e2ha_ensembl_gene_id": "ENSG000001",
                    "e2ha_mapped": "Reference",
                },
                {
                    "e2ha_hgnc_id": 5,
                    "e2ha_ensembl_gene_id": "ENSG999999",
                    "e2ha_mapped": "Alt-loci",
                },
                {
                    "e2ha_hgnc_id": 7,
                    "e2ha_ensembl_gene_id": "ENSG000007",
                    "e2ha_mapped": "Alt-loci",
                },
            ]
            mock_repo_cls.return_value = mock_repo

            loader = Ensembl2HgncCompleteLoader()
            rows = loader.fetch_and_parse()

    assert rows == [
        {
            "e2ha_hgnc_id": 5,
            "e2ha_ensembl_gene_id": "ENSG000001",
            "e2ha_mapped": "Reference",
        },
        {
            "e2ha_hgnc_id": 7,
            "e2ha_ensembl_gene_id": "ENSG000007",
            "e2ha_mapped": "Alt-loci",
        },
    ]


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
    assert rows == [
        {"eseq_source": "Homo_sapiens.GRCh38.cdna.all.fa.gz"},
        {"eseq_source": "Homo_sapiens.GRCh38.ncrna.fa.gz"},
    ]


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


def test_imgt_loader_ignores_empty_extra_column() -> None:
    row = "species;id;fn;name;alleles;chrom;acc;sym;5;123;vega;atlas;cards;P12345;"
    html = f"<html><pre>header\n{row}\n</pre></html>".encode("utf-8")
    fetch_client = MagicMock()
    fetch_client.fetch.return_value = html

    loader = ImgtLoader(fetch_client=fetch_client)
    rows = loader.fetch_and_parse()

    assert len(rows) == 1
    assert rows[0]["im_uniprot"] == "P12345"


def test_imgt_loader_raises_on_non_empty_extra_column() -> None:
    row = "species;id;fn;name;alleles;chrom;acc;sym;5;123;vega;atlas;cards;P12345;extra"
    html = f"<html><pre>header\n{row}\n</pre></html>".encode("utf-8")
    fetch_client = MagicMock()
    fetch_client.fetch.return_value = html

    loader = ImgtLoader(fetch_client=fetch_client)

    try:
        loader.fetch_and_parse()
        assert False, "Expected ValueError for non-empty extra IMGT column"
    except ValueError as exc:
        assert "extra IMGT column" in str(exc)


def test_cytoband_loader_parses_ucsc_rows() -> None:
    content = "chr1\t100\t200\tp36.33\tgneg\n"
    import gzip

    fetch_client = MagicMock()
    fetch_client.fetch.return_value = gzip.compress(content.encode("utf-8"))

    loader = CytobandLoader(fetch_client=fetch_client)
    rows = loader.fetch_and_parse()

    assert rows == [
        {
            "cb_source": "UCSC",
            "cb_chr": "1",
            "cb_start": 100,
            "cb_end": 200,
            "cb_band": "p36.33",
            "cb_stain": "gneg",
        }
    ]


def test_ucsc2hgnc_loader_parses_hgnc_xref_rows() -> None:
    content = "A1BG\tHGNC:5\tuc001aaa.3\n"
    import gzip

    fetch_client = MagicMock()
    fetch_client.fetch.return_value = gzip.compress(content.encode("utf-8"))

    loader = Ucsc2HgncLoader(fetch_client=fetch_client)
    rows = loader.fetch_and_parse()

    assert rows == [
        {
            "ucsc_hgnc_app_sym": "A1BG",
            "ucsc_hgnc_id": "5",
            "ucsc_hgnc_ucsc_id": "uc001aaa.3",
            "ucsc_mapby": "M",
        }
    ]


def test_ucsc2hgnc_loader_marks_subsequent_duplicate_ids_with_dash() -> None:
    content = "A1BG\tHGNC:5\tuc001aaa.3\nA1BG\tHGNC:5\tuc001bbb.1\n"
    import gzip

    fetch_client = MagicMock()
    fetch_client.fetch.return_value = gzip.compress(content.encode("utf-8"))

    loader = Ucsc2HgncLoader(fetch_client=fetch_client)
    rows = loader.fetch_and_parse()

    assert rows[0]["ucsc_mapby"] == "M"
    assert rows[1]["ucsc_mapby"] == "-"
