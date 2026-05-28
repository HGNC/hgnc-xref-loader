"""Tests for Ensembl2Hgnc staging and promotion service.

Validates the load service that orchestrates MySQL fetch, Postgres staging,
duplicate cleanup, and promotion for the ensembl2hgnc table.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from hgnc_xref_loader.repositories.ensembl2hgnc_repository import (
    Ensembl2HgncRecord,
)
from hgnc_xref_loader.services.ensembl2hgnc_load_service import (
    Ensembl2HgncLoadResult,
    Ensembl2HgncLoadService,
)


@pytest.fixture
def mock_ensembl_repo() -> MagicMock:
    repo = MagicMock()
    repo.fetch_mappings.return_value = [
        Ensembl2HgncRecord(
            hgnc_id="HGNC:9052",
            hgnc_symbol="PLAU",
            ensembl_gene_id="ENSG00000124383",
        ),
        Ensembl2HgncRecord(
            hgnc_id="HGNC:12853",
            hgnc_symbol="YWHAB",
            ensembl_gene_id="ENSG00000166947",
        ),
    ]
    return repo


@pytest.fixture
def mock_staging_repo() -> MagicMock:
    repo = MagicMock()
    repo.prepare_staging_table.return_value = "ensembl2hgnc_update"
    repo.bulk_copy_into_staging.return_value = 2
    return repo


@pytest.fixture
def mock_version_tracker() -> MagicMock:
    tracker = MagicMock()
    tracker.should_skip.return_value = False
    return tracker


class TestEnsembl2HgncLoadService:
    """Test the full load pipeline."""

    def test_run_fetches_and_stages(
        self,
        mock_ensembl_repo: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        service = Ensembl2HgncLoadService(
            ensembl_repo=mock_ensembl_repo,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
            ensembl_version="112",
        )
        result = service.run()

        mock_ensembl_repo.fetch_mappings.assert_called_once()
        mock_staging_repo.prepare_staging_table.assert_called_once_with(
            "ensembl2hgnc"
        )
        assert result.success is True
        assert result.rows_loaded == 2

    def test_run_performs_duplicate_cleanup(
        self,
        mock_ensembl_repo: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        service = Ensembl2HgncLoadService(
            ensembl_repo=mock_ensembl_repo,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
            ensembl_version="112",
        )
        result = service.run()

        mock_staging_repo.execute_cleanup.assert_called_once()
        assert result.success is True

    def test_run_promotes_after_cleanup(
        self,
        mock_ensembl_repo: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        service = Ensembl2HgncLoadService(
            ensembl_repo=mock_ensembl_repo,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
            ensembl_version="112",
        )
        result = service.run()

        mock_staging_repo.promote_staging_to_production.assert_called_once_with(
            "ensembl2hgnc_update", "ensembl2hgnc"
        )

    def test_run_records_version(
        self,
        mock_ensembl_repo: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        service = Ensembl2HgncLoadService(
            ensembl_repo=mock_ensembl_repo,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
            ensembl_version="112",
        )
        result = service.run()

        mock_version_tracker.record_version.assert_called_once_with(
            "ensembl2hgnc", "112"
        )

    def test_run_skips_when_version_unchanged(
        self,
        mock_ensembl_repo: MagicMock,
        mock_staging_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        mock_version_tracker.should_skip.return_value = True

        service = Ensembl2HgncLoadService(
            ensembl_repo=mock_ensembl_repo,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
            ensembl_version="112",
        )
        result = service.run()

        assert result.skipped is True
        mock_ensembl_repo.fetch_mappings.assert_not_called()


class TestEnsembl2HgncCleanupSql:
    """Test the duplicate cleanup SQL generation."""

    def test_cleanup_deletes_conflicting_hgnc_ids(
        self,
        mock_ensembl_repo: MagicMock,
        mock_version_tracker: MagicMock,
    ) -> None:
        mock_staging_repo = MagicMock()

        service = Ensembl2HgncLoadService(
            ensembl_repo=mock_ensembl_repo,
            staging_repo=mock_staging_repo,
            version_tracker=mock_version_tracker,
            ensembl_version="112",
        )
        cleanup_sql = service.get_cleanup_sql()

        assert "ensembl2hgnc_update" in cleanup_sql
        assert "e2h_hgnc_id" in cleanup_sql
        assert "e2h_ensembl_gene_id" in cleanup_sql
        assert "DELETE" in cleanup_sql
