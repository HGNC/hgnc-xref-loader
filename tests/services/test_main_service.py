"""Tests for MainService orchestration (Task 35)."""

from __future__ import annotations

import logging
import logging.handlers
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.config import Settings
from hgnc_xref_loader.loaders.registry import XrefSource
from hgnc_xref_loader.services.main_service import (
    LoadStatus,
    MainService,
    MainServiceResult,
)


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


class TestMainServiceVersionGating:
    """Test version-gated lifecycle in MainService.run()."""

    def test_run_skips_when_version_unchanged(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        mock_tracker = MagicMock()
        mock_tracker.should_skip.return_value = True

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            service = MainService(
                settings=mock_settings, version_tracker=mock_tracker
            )
            result = service.run()

        assert result.status == LoadStatus.SKIPPED
        assert result.success is True
        mock_svc_cls.return_value.run.assert_not_called()

    def test_run_proceeds_when_version_changed(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        mock_tracker = MagicMock()
        mock_tracker.should_skip.return_value = False

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 42
            mock_svc_cls.return_value = mock_svc

            service = MainService(
                settings=mock_settings, version_tracker=mock_tracker
            )
            result = service.run()

        assert result.status == LoadStatus.SUCCESS
        assert result.record_count == 42

    def test_run_without_version_tracker_always_runs(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "ccds"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 10
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        assert result.status == LoadStatus.SUCCESS
        assert result.record_count == 10


class TestMainServiceStructuredLogging:
    """Test structured logging with timestamps, duration, and status."""

    def test_run_emits_start_and_complete_logs(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 100
            mock_svc_cls.return_value = mock_svc

            handler = logging.handlers.MemoryHandler(capacity=100)
            logger = logging.getLogger("hgnc_xref_loader")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            try:
                service = MainService(settings=mock_settings)
                result = service.run()
            finally:
                logger.removeHandler(handler)

        buffer = handler.buffer
        start_logs = [r for r in buffer if r.getMessage() == "main_service_start"]
        complete_logs = [
            r for r in buffer if r.getMessage() == "main_service_complete"
        ]
        assert len(start_logs) == 1
        assert len(complete_logs) == 1

    def test_run_complete_log_contains_duration(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "gene_info"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 50
            mock_svc_cls.return_value = mock_svc

            handler = logging.handlers.MemoryHandler(capacity=100)
            logger = logging.getLogger("hgnc_xref_loader")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            try:
                service = MainService(settings=mock_settings)
                result = service.run()
            finally:
                logger.removeHandler(handler)

        complete_logs = [
            r
            for r in handler.buffer
            if r.getMessage() == "main_service_complete"
        ]
        assert len(complete_logs) == 1
        extra = complete_logs[0].__dict__
        assert "duration_seconds" in extra

    def test_run_failure_log_contains_error_details(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("disk full")
            mock_svc_cls.return_value = mock_svc

            handler = logging.handlers.MemoryHandler(capacity=100)
            logger = logging.getLogger("hgnc_xref_loader")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            try:
                service = MainService(settings=mock_settings)
                result = service.run()
            finally:
                logger.removeHandler(handler)

        error_logs = [
            r for r in handler.buffer if r.getMessage() == "main_service_failed"
        ]
        assert len(error_logs) == 1


class TestMainServiceResultStatus:
    """Test MainServiceResult status field semantics."""

    def test_success_result_has_success_status(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 10
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        assert result.status == LoadStatus.SUCCESS
        assert result.success is True

    def test_exception_result_has_failed_status(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("boom")
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        assert result.status == LoadStatus.FAILED
        assert result.success is False

    def test_empty_source_has_failed_status(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = ""

        service = MainService(settings=mock_settings)
        result = service.run()

        assert result.status == LoadStatus.FAILED

    def test_result_contains_started_at_and_finished_at(self) -> None:
        mock_settings = MagicMock()
        mock_settings.runtime.xref_source = "uniprot"

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 10
            mock_svc_cls.return_value = mock_svc

            service = MainService(settings=mock_settings)
            result = service.run()

        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.finished_at >= result.started_at
