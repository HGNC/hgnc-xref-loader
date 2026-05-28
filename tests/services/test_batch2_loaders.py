"""Tests for batch 2 HTTP loaders: gencc, iuphar, mane, omim2gene, rgd_orthologs, agr, mgi."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.gencc_parser import GenCCParser
from hgnc_xref_loader.loaders.iuphar_parser import IupharParser
from hgnc_xref_loader.loaders.mane_parser import ManeParser
from hgnc_xref_loader.loaders.omim2gene_parser import Omim2GeneParser
from hgnc_xref_loader.loaders.rgd_orthologs_parser import RgdOrthologsParser
from hgnc_xref_loader.loaders.agr_parser import AgrParser
from hgnc_xref_loader.loaders.mgi_parser import MgiParser

from hgnc_xref_loader.services.gencc_load_service import GenCCLoadService
from hgnc_xref_loader.services.iuphar_load_service import IupharLoadService
from hgnc_xref_loader.services.mane_load_service import ManeLoadService
from hgnc_xref_loader.services.omim2gene_load_service import Omim2GeneLoadService
from hgnc_xref_loader.services.rgd_orthologs_load_service import RgdOrthologsLoadService
from hgnc_xref_loader.services.agr_load_service import AgrLoadService
from hgnc_xref_loader.services.mgi_load_service import MgiLoadService


def _make_gencc_csv() -> bytes:
    return (
        b"uuid, hgnc_id, gene_symbol, disease_id, disease_title, disease_url\n"
        b'"abc-123","HGNC:5","A1BG","OMIM:123456","Some disease","OMIM:654321"\n'
        b'"def-456","HGNC:7","A2M","","Another disease",""\n'
    )


def _make_iuphar_csv() -> bytes:
    return (
        b"Symbol,HGNC_ID,Name,Target_URL,Receptor_URL,Receptor_ID\n"
        b'"A1BG","5","A1BG name","http://example.com?objectId=123","http://r/456","456"\n'
    )


def _make_mane_tsv() -> bytes:
    header = (
        "NCBI_GeneID\tEnsembl_Gene\tHGNC_ID\tsymbol\tname\t"
        "RefSeq_nuc\tRefSeq_prot\tEnsembl_nuc\tEnsembl_prot\t"
        "MANE_status\tGRCh38_chr\tGRCh38_start\tGRCh38_end\tGRCh38_strand\n"
    )
    lines = (
        "GeneID:1\tENSG00000121410.5\tHGNC:5\tA1BG\talpha-1-B glycoprotein\t"
        "NM_001308203.2\tNP_001295132.1\tENST00000274589.7\tENSP00000274589.2\t"
        "MANE Select\tchr19\t58345186\t58353092\t+\n"
    )
    return gzip.compress((header + lines).encode("utf-8"))


def _make_omim2gene_tsv() -> bytes:
    return (
        b"# MIM_number\tType\tEntrez_Gene_ID\tSymbol\tEnsembl_ID\n"
        b"100100\tgene\t1\tA1BG\tENSG00000121410\n"
        b"100200\tphenotype\t-\t-\t-\n"
    )


def _make_rgd_orthologs_tsv() -> bytes:
    return (
        b"rat_sym\trat_rgd\trat_eg\thuman_sym\thuman_rgd\thuman_eg\t"
        b"human_src\tmouse_sym\tmouse_rgd\tmouse_eg\tmouse_mgi\tmouse_src\t"
        b"human_hgnc\n"
        b"Rat1\t1001\t2001\tA1BG\t3001\t4001\tRGD\tMouse1\t5001\t6001\t"
        b"MGI:12345\tRGD\tHGNC:5\n"
    )


def _make_agr_tsv() -> bytes:
    return (
        b"HGNC_ID\tSymbol\tDescription\n"
        b"HGNC:5\tA1BG\tAlpha-1-B glycoprotein\n"
        b"HGNC:7\tA2M\tNo description available\n"
    )


def _make_mgi_tsv() -> bytes:
    return (
        b"MGI_ID\tSymbol\tName\tType\tNCBI_GeneID\tNCBI_Chr\tNCBI_Start\t"
        b"NCBI_End\tNCBI_Strand\tEnsembl_ID\tEnsembl_Chr\tEnsembl_Start\t"
        b"Ensembl_End\tEnsembl_Strand\n"
        b"MGI:87874\tA1bg\talpha-1-B glycoprotein\tProtein Coding Gene\t"
        b"1\t12\t12345\t67890\t+\tENSMUSG0000001\t12\t12345\t67890\t-\n"
    )


class TestGenCCParser:
    def test_parse_extracts_hgnc_and_omim(self) -> None:
        records = GenCCParser().parse(_make_gencc_csv())
        assert len(records) == 2
        assert records[0].hgnc_id == 5
        assert records[0].omim_id == 654321
        assert records[1].omim_id == 0

    def test_parse_staging_dict(self) -> None:
        records = GenCCParser().parse(_make_gencc_csv())
        d = records[0].to_staging_dict()
        assert d["hgnc_id"] == 5
        assert len(d) == 5


class TestGenCCLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_gencc_csv()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "gencc_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = GenCCLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True
        assert result.rows_loaded == 2


class TestIupharParser:
    def test_parse_basic(self) -> None:
        records = IupharParser().parse(_make_iuphar_csv())
        assert len(records) == 1
        assert records[0].iu_hgnc_id == 5
        assert records[0].iu_app_sym == "A1BG"

    def test_parse_staging_dict(self) -> None:
        records = IupharParser().parse(_make_iuphar_csv())
        d = records[0].to_staging_dict()
        assert len(d) == 5


class TestIupharLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_iuphar_csv()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "iuphar_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = IupharLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True


class TestManeParser:
    def test_parse_strips_prefixes(self) -> None:
        records = ManeParser().parse(_make_mane_tsv())
        assert len(records) == 1
        assert records[0].ncbi_gene_id == 1
        assert records[0].hgnc_id == 5
        assert records[0].id == 1

    def test_parse_staging_dict(self) -> None:
        records = ManeParser().parse(_make_mane_tsv())
        d = records[0].to_staging_dict()
        assert len(d) == 15


class TestManeLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.side_effect = [
            b"MANE Version 1.4\nEnsembl Release 112\n",
            _make_mane_tsv(),
        ]
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "mane_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = ManeLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True


class TestOmim2GeneParser:
    def test_parse_basic(self) -> None:
        records = Omim2GeneParser().parse(_make_omim2gene_tsv())
        assert len(records) == 2
        assert records[0].m2g_mim_number == "100100"

    def test_parse_staging_dict(self) -> None:
        records = Omim2GeneParser().parse(_make_omim2gene_tsv())
        d = records[0].to_staging_dict()
        assert len(d) == 5


class TestOmim2GeneLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_omim2gene_tsv()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "omim2gene_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = Omim2GeneLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True


class TestRgdOrthologsParser:
    def test_parse_strips_hgnc_prefix(self) -> None:
        records = RgdOrthologsParser().parse(_make_rgd_orthologs_tsv())
        assert len(records) == 1
        assert records[0].rgdo_human_ortholog_hgnc_id == "5"

    def test_parse_staging_dict(self) -> None:
        records = RgdOrthologsParser().parse(_make_rgd_orthologs_tsv())
        d = records[0].to_staging_dict()
        assert len(d) == 13


class TestRgdOrthologsLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_rgd_orthologs_tsv()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "rgd_orthologs_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = RgdOrthologsLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True


class TestAgrParser:
    def test_parse_strips_hgnc_prefix(self) -> None:
        records = AgrParser().parse(_make_agr_tsv())
        assert len(records) == 2
        assert records[0].hgnc_id == 5

    def test_parse_clears_no_description(self) -> None:
        records = AgrParser().parse(_make_agr_tsv())
        assert records[1].description == ""


class TestAgrLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_agr_tsv()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "agr_update"
        mock_staging.bulk_copy_into_staging.return_value = 2
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = AgrLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True


class TestMgiParser:
    def test_parse_basic(self) -> None:
        records = MgiParser().parse(_make_mgi_tsv())
        assert len(records) == 1
        assert records[0].mgi_id == "MGI:87874"
        assert records[0].symbol == "A1bg"

    def test_parse_staging_dict(self) -> None:
        records = MgiParser().parse(_make_mgi_tsv())
        d = records[0].to_staging_dict()
        assert len(d) == 14


class TestMgiLoadService:
    def test_run_success(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_mgi_tsv()
        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "mgi_update"
        mock_staging.bulk_copy_into_staging.return_value = 1
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        result = MgiLoadService(mock_http, mock_staging, mock_version).run()
        assert result.success is True
