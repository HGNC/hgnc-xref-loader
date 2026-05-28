"""Tests for the gene_history parser and load service."""

from __future__ import annotations

import gzip
from unittest.mock import MagicMock

from hgnc_xref_loader.loaders.gene_history_parser import (
    GeneHistoryParser,
    GeneHistoryRecord,
)
from hgnc_xref_loader.services.gene_history_load_service import (
    GeneHistoryLoadResult,
    GeneHistoryLoadService,
)


def _make_gene_history_tsv() -> bytes:
    header = "#tax_id\tGeneID\tDiscontinued_GeneID\tDiscontinued_Symbol\tDiscontinued_Date\n"
    lines = (
        "9606\t1\t100000001\tOLDGENE1\t2020-01-01\n"
        "10090\t2\t100000002\tOLDGENE2\t2020-02-02\n"
        "10116\t3\t100000003\tOLDGENE3\t2020-03-03\n"
        "3702\t4\t100000004\tOLDGENE4\t2020-04-04\n"
    )
    return gzip.compress((header + lines).encode("utf-8"))


class TestGeneHistoryParser:
    """Test the gene_history TSV parser."""

    def test_parse_filters_by_tax_id(self) -> None:
        parser = GeneHistoryParser()
        records = parser.parse(_make_gene_history_tsv())
        assert len(records) == 3
        tax_ids = {r.gh_tax_id for r in records}
        assert tax_ids == {"9606", "10090", "10116"}

    def test_parse_empty_input(self) -> None:
        parser = GeneHistoryParser()
        records = parser.parse(gzip.compress(b"#tax_id\t\n"))
        assert records == []

    def test_parse_record_fields(self) -> None:
        parser = GeneHistoryParser()
        records = parser.parse(_make_gene_history_tsv())
        human = [r for r in records if r.gh_tax_id == "9606"][0]
        assert human.gh_eg_id == "1"
        assert human.gh_discontinued_eg_id == "100000001"
        assert human.gh_discontinued_sym == "OLDGENE1"
        assert human.gh_discontinued_date == "2020-01-01"

    def test_parse_staging_dict(self) -> None:
        parser = GeneHistoryParser()
        records = parser.parse(_make_gene_history_tsv())
        human = [r for r in records if r.gh_tax_id == "9606"][0]
        d = human.to_staging_dict()
        assert d["gh_tax_id"] == "9606"
        assert d["gh_eg_id"] == "1"

    def test_parse_dash_becomes_empty(self) -> None:
        parser = GeneHistoryParser()
        tsv = (
            "#tax_id\tGeneID\tDiscontinued_GeneID\tDiscontinued_Symbol\tDiscontinued_Date\n"
            "9606\t1\t-\tOLDGENE\t-\n"
        )
        records = parser.parse(gzip.compress(tsv.encode("utf-8")))
        assert records[0].gh_discontinued_eg_id == ""
        assert records[0].gh_discontinued_date == ""


class TestGeneHistoryLoadService:
    """Test the load service orchestration."""

    def test_run_fetches_and_stages(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.return_value = _make_gene_history_tsv()

        mock_staging = MagicMock()
        mock_staging.prepare_staging_table.return_value = "gene_history_update"
        mock_staging.bulk_copy_into_staging.return_value = 3

        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = GeneHistoryLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is True
        assert result.rows_loaded == 3
        mock_staging.promote_staging_to_production.assert_called_once()

    def test_run_skips_when_version_unchanged(self) -> None:
        mock_http = MagicMock()
        mock_staging = MagicMock()
        mock_version = MagicMock()
        mock_version.should_skip.return_value = True

        service = GeneHistoryLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.skipped is True
        mock_http.fetch.assert_not_called()

    def test_run_returns_error_on_failure(self) -> None:
        mock_http = MagicMock()
        mock_http.fetch.side_effect = RuntimeError("network error")

        mock_staging = MagicMock()
        mock_version = MagicMock()
        mock_version.should_skip.return_value = False

        service = GeneHistoryLoadService(
            http_client=mock_http,
            staging_repo=mock_staging,
            version_tracker=mock_version,
        )
        result = service.run()

        assert result.success is False
        assert "network error" in result.error
