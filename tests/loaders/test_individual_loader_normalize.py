"""Tests for normalize() mappings in individual loaders."""

from __future__ import annotations

from hgnc_xref_loader.loaders.individual_loaders import (
    AgrLoader,
    EnsemblGeneLoader,
    GeneInfoLoader,
    ImgtLoader,
    LovdLoader,
    Ucsc2HgncLoader,
)


def test_gene_info_normalize_maps_fields_to_xrefrecord() -> None:
    loader = GeneInfoLoader()
    records = loader.normalize(
        [
            {
                "gi_hgnc_id": 5,
                "gi_eg_id": "1",
                "gi_sym": "A1BG",
                "gi_nome_status": "O",
            }
        ]
    )
    assert len(records) == 1
    assert records[0].hgnc_id == "5"
    assert records[0].external_id == "1"
    assert records[0].source == "gene_info"
    assert records[0].symbol == "A1BG"


def test_ensembl_gene_normalize_maps_core_fields() -> None:
    loader = EnsemblGeneLoader()
    records = loader.normalize(
        [
            {
                "hgnc_id": 5,
                "gene_id": "ENSG00000121410",
                "name": "A1BG",
                "name_source": "HGNC",
            }
        ]
    )
    assert len(records) == 1
    assert records[0].hgnc_id == "5"
    assert records[0].external_id == "ENSG00000121410"
    assert records[0].source == "ensembl_gene"


def test_lovd_normalize_uses_gene_symbol_and_url() -> None:
    loader = LovdLoader()
    records = loader.normalize(
        [{"lovd_db_genes": "NF1", "lovd_db_url": "http://lovd.test/NF1"}]
    )
    assert len(records) == 1
    assert records[0].hgnc_id == "NF1"
    assert records[0].external_id == "http://lovd.test/NF1"
    assert records[0].symbol == "NF1"


def test_ucsc2hgnc_normalize_uses_hgnc_and_transcript() -> None:
    loader = Ucsc2HgncLoader()
    records = loader.normalize(
        [
            {
                "ucsc_hgnc_id": "HGNC:5",
                "ucsc_hgnc_ucsc_id": "uc001aaa.3",
                "ucsc_hgnc_app_sym": "A1BG",
                "ucsc_mapby": "M",
            }
        ]
    )
    assert len(records) == 1
    assert records[0].hgnc_id == "HGNC:5"
    assert records[0].external_id == "uc001aaa.3"
    assert records[0].status == "M"


def test_imgt_normalize_falls_back_keys() -> None:
    loader = ImgtLoader()
    records = loader.normalize(
        [
            {
                "im_hgnc_id": "5",
                "im_gene_id": "IGHV1-2",
                "im_hgnc_app_sym": "IGHV1-2",
                "im_gene_function": "V-REGION",
            }
        ]
    )
    assert len(records) == 1
    assert records[0].hgnc_id == "5"
    assert records[0].external_id == "IGHV1-2"
    assert records[0].symbol == "IGHV1-2"


def test_normalize_skips_blank_rows() -> None:
    loader = AgrLoader()
    records = loader.normalize([{"hgnc_id": "", "description": "-"}])
    assert records == []
