"""Tests for ncbi2namelist parser and load service."""

from __future__ import annotations

from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.ncbi2namelist_parser import Ncbi2NamelistParser
from hgnc_xref_loader.services.ncbi2namelist_load_service import (
    Ncbi2NamelistLoadService,
)


def _make_namelist_data() -> bytes:
    return b"1\tA1BG\n2\tA2M\n3\tA3GALT2\n"


class TestNcbi2NamelistParser:
    """Test the ncbi2namelist TSV parser."""

    def test_parse_basic(self) -> None:
        parser = Ncbi2NamelistParser()
        records = parser.parse(_make_namelist_data())
        assert len(records) == 3

    def test_parse_record_fields(self) -> None:
        parser = Ncbi2NamelistParser()
        records = parser.parse(_make_namelist_data())
        assert records[0].ntn_eg_id == "1"
        assert records[0].ntn_sym == "A1BG"

    def test_parse_skips_short_lines(self) -> None:
        parser = Ncbi2NamelistParser()
        data = b"1\tA1BG\nempty_line\n2\tA2M\n"
        records = parser.parse(data)
        assert len(records) == 2


class TestNcbi2NamelistLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_fetch = MagicMock()
        mock_fetch.fetch.return_value = _make_namelist_data()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "ncbi2namelist_update"
        mock_staging.bulk_copy_into_staging.return_value = 3

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = Ncbi2NamelistLoadService(
            fetch_client=mock_fetch,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 3
