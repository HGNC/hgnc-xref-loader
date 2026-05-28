"""Tests for batch 3 database loaders: ensembl2hgnc_complete, ensembl_gene, ensembl_seq."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.ensembl_seq_parser import EnsemblSeqParser
from hgnc_xref_loader.services.ensembl2hgnc_complete_load_service import (
    Ensembl2HgncCompleteLoadService,
)
from hgnc_xref_loader.services.ensembl_gene_load_service import (
    EnsemblGeneLoadService,
)
from hgnc_xref_loader.services.ensembl_seq_load_service import EnsemblSeqLoadService


def _make_cdna_fasta() -> bytes:
    fasta = (
        ">ENST00000274589.7 cdna chromosome:GRCh38:19:58345186:58353092:1 "
        "gene:ENSG00000121410.5 gene_biotype:protein_coding "
        "transcript_biotype:protein_coding gene_symbol:A1BG "
        "description:some description [Source:HGNC Symbol%3BAcc:HGNC:5]\n"
        "ATCGATCG\n"
        "GCTAGCTA\n"
    )
    return gzip.compress(fasta.encode("utf-8"))


def _make_ncrna_fasta() -> bytes:
    fasta = (
        ">ENST00000435765.1 cdna chromosome:GRCh38:19:58347359:58347740:-1 "
        "gene:ENSG00000257655.1 gene_biotype:lncRNA "
        "transcript_biotype:lncRNA gene_symbol:AL133304.1\n"
        "TTTTTTTT\n"
    )
    return gzip.compress(fasta.encode("utf-8"))


class TestEnsemblSeqParser:
    def test_parse_cdna(self) -> None:
        records = EnsemblSeqParser().parse_cdna(_make_cdna_fasta())
        assert len(records) == 1
        assert records[0].eseq_source == "cdna"
        assert records[0].eseq_ensembl_gene_id == "ENSG00000121410"
        assert records[0].eseq_ensembl_transcript_id == "ENST00000274589"
        assert records[0].eseq_seq == "ATCGATCGGCTAGCTA"
        assert records[0].eseq_length == 16

    def test_parse_ncrna(self) -> None:
        records = EnsemblSeqParser().parse_ncrna(_make_ncrna_fasta())
        assert len(records) == 1
        assert records[0].eseq_source == "ncrna"
        assert records[0].eseq_ensembl_gene_id == "ENSG00000257655"

    def test_staging_dict(self) -> None:
        records = EnsemblSeqParser().parse_cdna(_make_cdna_fasta())
        d = records[0].to_staging_dict()
        assert len(d) == 6
        assert d["eseq_length"] == 16


class TestEnsembl2HgncCompleteLoadService:
    def test_run_success(self) -> None:
        mock_ensembl = MagicMock()
        mock_ensembl.fetch_all_mappings.return_value = [
            {"e2ha_hgnc_id": 5, "e2ha_app_sym": "A1BG",
             "e2ha_ensembl_gene_id": "ENSG00000121410", "e2ha_biotype": "protein_coding",
             "e2ha_mapped": "Reference"},
        ]
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "ensembl2hgnc_all_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = Ensembl2HgncCompleteLoadService(
            mock_ensembl, mock_staging, mock_version
        ).run()
        assert result.success is True
        assert result.rows_loaded == 1


class TestEnsemblGeneLoadService:
    def test_run_success(self) -> None:
        mock_ensembl = MagicMock()
        mock_ensembl.fetch_genes.return_value = [
            {"name": "A1BG", "name_source": "HGNC Symbol",
             "gene_id": "ENSG00000121410", "biotype": "protein_coding",
             "chromosome": "19", "hgnc_id": 5, "on_alt_loci": False},
        ]
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "ensembl_gene_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = EnsemblGeneLoadService(
            mock_ensembl, mock_staging, mock_version
        ).run()
        assert result.success is True


class TestEnsemblSeqLoadService:
    def test_run_success(self) -> None:
        mock_ftp = MagicMock()
        mock_ftp.fetch_cdna.return_value = _make_cdna_fasta()
        mock_ftp.fetch_ncrna.return_value = _make_ncrna_fasta()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "ensembl_seq_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = EnsemblSeqLoadService(
            mock_ftp, mock_staging, mock_version
        ).run()
        assert result.success is True
        assert result.rows_loaded == 2
