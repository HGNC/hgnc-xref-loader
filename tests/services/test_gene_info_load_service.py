"""Tests for gene_info loader service.

Validates the gene_info NCBI loader: HTTP download, gzip decompression,
tax_id filtering, HGNC ID extraction, and staging.
"""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

import pytest

from hgnc_xref_loader.loaders.gene_info_parser import GeneInfoParser, GeneInfoRecord
from hgnc_xref_loader.services.gene_info_load_service import (
    GeneInfoLoadResult,
    GeneInfoLoadService,
)


def _make_gene_info_tsv() -> bytes:
    header = (
        "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\t"
        "dbXrefs\tchromosome\tmap_location\tdescription\t"
        "type_of_gene\tSymbol_from_nomenclature_authority\t"
        "Full_name_from_nomenclature_authority\t"
        "Nomenclature_status\tOther_designations\t"
        "Modification_date\tFeature_type\n"
    )
    rows = (
        "9606\t1\tA1BG\t-\tA1B|ABH|\tHGNC:5|MIM:138670\t19\t19q13.4\t"
        "alpha-1-B glycoprotein\tprotein_coding\tA1BG\t"
        "alpha-1-B glycoprotein\tO\talpha-1B-glycoprotein\t"
        "20240101\tprotein_coding\n"
        "9606\t2\tA2M\t-\tACP|CPAMD5|\tHGNC:7|MIM:103950\t12\t12p13.31\t"
        "alpha-2-macroglobulin\tprotein_coding\tA2M\t"
        "alpha-2-macroglobulin\tO\talpha-2-macroglobulin\t"
        "20240102\tprotein_coding\n"
        "10090\t3\tA2mp\t-\t-\tMGI:87991\t7\t7 F3\t"
        "mouse protein\tprotein_coding\tA2mp\t"
        "murine protein\tO\tdesignation\t"
        "20240103\tprotein_coding\n"
    )
    return gzip.compress((header + rows).encode("utf-8"))


class TestGeneInfoParser:
    """Test the gene_info TSV parser."""

    def test_parse_extracts_human_rows(self) -> None:
        parser = GeneInfoParser()
        records = parser.parse(_make_gene_info_tsv())
        assert len(records) == 3

    def test_parse_extracts_hgnc_id(self) -> None:
        parser = GeneInfoParser()
        records = parser.parse(_make_gene_info_tsv())
        human = [r for r in records if r.gi_tax_id == "9606"]
        assert human[0].gi_hgnc_id == 5
        assert human[1].gi_hgnc_id == 7

    def test_parse_includes_mouse_rat(self) -> None:
        parser = GeneInfoParser()
        records = parser.parse(_make_gene_info_tsv())
        tax_ids = {r.gi_tax_id for r in records}
        assert "9606" in tax_ids
        assert "10090" in tax_ids

    def test_parse_excludes_unknown_tax(self) -> None:
        parser = GeneInfoParser()
        records = parser.parse(_make_gene_info_tsv())
        tax_ids = {r.gi_tax_id for r in records}
        assert "7955" not in tax_ids

    def test_parse_staging_dict(self) -> None:
        parser = GeneInfoParser()
        records = parser.parse(_make_gene_info_tsv())
        human = [r for r in records if r.gi_tax_id == "9606"]
        d = human[0].to_staging_dict()
        assert d["gi_tax_id"] == "9606"
        assert d["gi_eg_id"] == "1"
        assert d["gi_sym"] == "A1BG"
        assert d["gi_hgnc_id"] == 5

    def test_parse_empty_gzip(self) -> None:
        parser = GeneInfoParser()
        records = parser.parse(gzip.compress(b""))
        assert records == []


class TestGeneInfoLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_gene_info_tsv()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "gene_info_update"
        mock_staging.bulk_copy_into_staging.return_value = 3

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = GeneInfoLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 3
        mock_staging.promote_staging_to_production.assert_called_once()

    def test_run_records_version(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_gene_info_tsv()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "gene_info_update"
        mock_staging.bulk_copy_into_staging.return_value = 0

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = GeneInfoLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
            source_version="01-Jan-2024",
        )
        service.run()

        mock_version.record_version.assert_called_once_with("gene_info", "01-Jan-2024")

    def test_run_skips_when_version_unchanged(self) -> None:
        mock_http = MagicMock()
        mock_staging = MagicMock()
        mock_version = MagicMock()
        mock_version.should_skip.return_value = True

        service = GeneInfoLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.skipped is True
        mock_http.fetch.assert_not_called()
