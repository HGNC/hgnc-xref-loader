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
    tracker.is_current_version.return_value = False
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
        mock_version_tracker.is_current_version.return_value = True

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
