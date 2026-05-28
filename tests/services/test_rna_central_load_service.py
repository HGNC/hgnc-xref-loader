"""Tests for rna_central parser and load service."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.rna_central_parser import RnaCentralParser
from hgnc_xref_loader.services.rna_central_load_service import (
    RnaCentralLoadService,
)


def _make_rna_central_tsv() -> bytes:
    header = "UCSC\tdatabase\tdatabase_id\tspecies\tsome_col\tsymbol\n"
    lines = (
        "URS0000000001\tHGNC\tHGNC:5\tHomo sapiens\tlncRNA\tA1BG\n"
        "URS0000000002\tMGI\tMGI:12345\tMus musculus\tmRNA\tGeneX\n"
        "URS0000000003\tHGNC\tHGNC:7\tHomo sapiens\tmisc_RNA\tA2M\n"
    )
    return gzip.compress((header + lines).encode("utf-8"))


class TestRnaCentralParser:
    """Test the rna_central TSV parser."""

    def test_parse_filters_hgnc_only(self) -> None:
        parser = RnaCentralParser()
        records = parser.parse(_make_rna_central_tsv())
        assert len(records) == 2

    def test_parse_strips_hgnc_prefix(self) -> None:
        parser = RnaCentralParser()
        records = parser.parse(_make_rna_central_tsv())
        assert records[0].hgnc_id == "5"
        assert records[1].hgnc_id == "7"

    def test_parse_assigns_sequential_ids(self) -> None:
        parser = RnaCentralParser()
        records = parser.parse(_make_rna_central_tsv())
        assert records[0].id == 1
        assert records[1].id == 2

    def test_parse_record_fields(self) -> None:
        parser = RnaCentralParser()
        records = parser.parse(_make_rna_central_tsv())
        assert records[0].rna_central_acc == "URS0000000001"
        assert records[0].symbol == "A1BG"


class TestRnaCentralLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_rna_central_tsv()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "rna_central_update"
        mock_staging.bulk_copy_into_staging.return_value = 2

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = RnaCentralLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 2
