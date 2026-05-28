"""Tests for the UniProt load service.

Validates the full orchestration: fetch -> parse -> stage -> promote
across the 4 UniProt tables with version tracking.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.services.uniprot_load_service import (
    UniprotLoadService,
)
from hgnc_xref_loader.loaders.uniprot_parser import UniprotTsvParser
from hgnc_xref_loader.loaders.uniprot_schemas import (
    UNIPROT_HEADER_LINES,
    UniprotHasEcSchema,
    UniprotHasHgncSchema,
    UniprotHasNcbiGeneSchema,
    UniprotMainSchema,
)


@pytest.fixture
def mock_http_client() -> MagicMock:
    client = MagicMock()
    client.fetch.return_value = (
        b"comment\n" * 19
        + b"Entry\tStatus\tEntry Name\tProtein names\tGene Names (primary)\t"
        b"Cross-reference (HGNC)\tEC number\tCross-reference (GeneID)\n"
        b"P00750\treviewed\tUROT_HUMAN\tUrokinase activator (EC 3.4.21)\tPLAU\tHGNC:9052\t3.4.21.73\t1234\n",
        "2024_03",
    )
    client.fetch_version.return_value = "2024_03"
    return client


@pytest.fixture
def mock_staging_repo() -> MagicMock:
    repo = MagicMock()
    repo.prepare_staging_tables.return_value = {
        "uniprot_update": "uniprot_update",
        "uniprot_has_hgnc_update": "uniprot_has_hgnc_update",
        "uniprot_has_ncbi_gene_update": "uniprot_has_ncbi_gene_update",
        "uniprot_has_ec_update": "uniprot_has_ec_update",
    }
    repo.bulk_load_main.return_value = 1
    repo.bulk_load_hgnc.return_value = 1
    repo.bulk_load_ncbi_gene.return_value = 1
    repo.bulk_load_ec.return_value = 1
    return repo


@pytest.fixture
def mock_version_tracker() -> MagicMock:
    tracker = MagicMock()
    tracker.should_skip.return_value = False
    tracker.record_version.return_value = None
    return tracker


class TestUniprotLoadServiceOrchestration:
    """Test the full fetch->parse->stage->promote pipeline."""

    def test_run_calls_fetch_parse_stage_promote(
        self,
        mock_http_client: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        service = UniprotLoadService(
            http_client=mock_http_client,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
        )
        result = service.run()

        mock_http_client.fetch.assert_called_once()
        mock_staging_repo.prepare_staging_tables.assert_called_once()
        mock_staging_repo.bulk_load_main.assert_called_once()
        mock_staging_repo.promote_all.assert_called_once()
        assert result.success is True

    def test_run_records_version_on_success(
        self,
        mock_http_client: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        service = UniprotLoadService(
            http_client=mock_http_client,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
        )
        result = service.run()

        mock_version_tracker.record_version.assert_called_once_with(
            "uniprot", "2024_03"
        )
        assert result.version == "2024_03"

    def test_run_skips_when_version_unchanged(
        self,
        mock_http_client: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        mock_version_tracker.should_skip.return_value = True

        service = UniprotLoadService(
            http_client=mock_http_client,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
        )
        result = service.run()

        assert result.success is True
        assert result.skipped is True
        mock_http_client.fetch.assert_not_called()
        mock_staging_repo.promote_all.assert_not_called()

    def test_run_returns_row_counts(
        self,
        mock_http_client: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        service = UniprotLoadService(
            http_client=mock_http_client,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
        )
        result = service.run()

        assert result.main_rows == 1
        assert result.hgnc_rows == 1
        assert result.ncbi_gene_rows == 1
        assert result.ec_rows == 1

    def test_run_does_not_record_version_on_fetch_failure(
        self,
        mock_http_client: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        from hgnc_xref_loader.fetch.uniprot_client import UniprotFetchError

        mock_http_client.fetch.side_effect = UniprotFetchError(
            url="https://test", reason="down"
        )

        service = UniprotLoadService(
            http_client=mock_http_client,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
        )
        result = service.run()

        assert result.success is False
        mock_version_tracker.record_version.assert_not_called()


class TestUniprotE2EParsing:
    """End-to-end parsing tests validating TSV -> staging row conversion."""

    def _make_tsv(self, data_rows: list[str]) -> bytes:
        header = (
            "Entry\tStatus\tEntry Name\tProtein names\tGene Names (primary)\t"
            "Cross-reference (HGNC)\tEC number\tCross-reference (GeneID)"
        )
        lines = ["comment"] * UNIPROT_HEADER_LINES + [header] + data_rows
        return "\n".join(lines).encode("utf-8")

    def test_e2e_multi_value_fields_populate_junction_tables(self) -> None:
        tsv = self._make_tsv([
            "P00750\treviewed\tUROT_HUMAN\tPlasminogen activator (EC 3.4.21)\tPLAU\t"
            "HGNC:9052;HGNC:1234\t3.4.21.73;1.1.1.1\t99;100;101",
        ])
        parser = UniprotTsvParser()
        batch = parser.parse(tsv)

        assert batch.total_main == 1
        assert batch.total_hgnc == 2
        assert batch.total_ec == 2
        assert batch.total_ncbi_gene == 3

    def test_e2e_schema_columns_match_parser_output(self) -> None:
        tsv = self._make_tsv([
            "P00750\treviewed\tUROT_HUMAN\tTest protein\tPLAU\tHGNC:9052\t3.4.21.73\t99",
        ])
        parser = UniprotTsvParser()
        batch = parser.parse(tsv)

        main_dict = batch.main_rows[0].to_dict()
        assert set(main_dict.keys()) == set(UniprotMainSchema.columns)

        hgnc_dict = batch.hgnc_rows[0].to_dict()
        assert set(hgnc_dict.keys()) == set(UniprotHasHgncSchema.columns)

        ec_dict = batch.ec_rows[0].to_dict()
        assert set(ec_dict.keys()) == set(UniprotHasEcSchema.columns)

        ncbi_dict = batch.ncbi_gene_rows[0].to_dict()
        assert set(ncbi_dict.keys()) == set(UniprotHasNcbiGeneSchema.columns)

    def test_e2e_version_recording_after_promotion(
        self,
        mock_http_client: MagicMock,
        mock_staging_repo: MagicMock,
    ) -> None:
        mock_version_tracker = MagicMock()
        mock_version_tracker.should_skip.return_value = False

        service = UniprotLoadService(
            http_client=mock_http_client,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
        )
        result = service.run()

        assert result.success is True
        assert result.version == "2024_03"
        mock_version_tracker.record_version.assert_called_once_with(
            "uniprot", "2024_03"
        )
