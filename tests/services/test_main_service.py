"""Tests for MainService orchestration (Task 35)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.config import Settings
from hgnc_xref_loader.loaders.registry import XrefSource
from hgnc_xref_loader.services.main_service import MainService


class TestMainServiceRun:
    """Test MainService.run() orchestration."""

    def test_run_resolves_source_from_settings(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 100
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        mock_svc_cls.assert_called_once()
        call_kwargs = mock_svc_cls.call_args[1]
        assert call_kwargs["source"] == XrefSource.UNIPROT

    def test_run_calls_xref_load_service_run(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "ccds"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 50
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        mock_svc.run.assert_called_once()

    def test_run_returns_result_with_record_count(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "gene_info"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 250
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        assert result.success is True
        assert result.record_count == 250

    def test_run_returns_failure_on_exception(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("loader crashed")
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        assert result.success is False
        assert "loader crashed" in result.error

    def test_run_returns_failure_on_empty_source(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = ""

        service = MainService(settings=mock_settings)
        result = service.run()

        assert result.success is False

    def test_run_returns_failure_on_unknown_source(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "nonexistent_source"

        service = MainService(settings=mock_settings)
        result = service.run()

        assert result.success is False

    def test_from_settings_creates_instance(self) -> None:
        mock_settings = MagicMock()
        service = MainService.from_settings(mock_settings)
        assert isinstance(service, MainService)
