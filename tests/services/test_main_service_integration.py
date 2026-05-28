"""Integration-style tests for MainService orchestration (Task 35.3).

Exercises MainService.run() end-to-end with mocked dependencies,
verifying loader selection, lifecycle invocation, logging, and error
propagation.
"""

from __future__ import annotations

import logging
import logging.handlers
from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.loaders.registry import XrefSource
from hgnc_xref_loader.services.main_service import (
    LoadStatus,
    MainService,
    MainServiceResult,
)


class _FakeSettings:
    """Minimal settings stub for integration tests."""

    def __init__(self, xref_source: str = "") -> None:
        self.runtime = MagicMock()
        self.runtime.xref_source = xref_source


class TestMainServiceIntegrationEndToEnd:
    """End-to-end integration tests for MainService.run()."""

    def test_single_source_uniprot_invokes_loader(self) -> None:
        settings = _FakeSettings(xref_source="uniprot")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 500
            mock_cls.return_value = mock_svc

            service = MainService(settings=settings)
            result = service.run()

        assert result.success is True
        assert result.record_count == 500
        assert result.status == LoadStatus.SUCCESS
        assert result.source == "uniprot"
        mock_cls.assert_called_once_with(
            source=XrefSource.UNIPROT, logger=service._logger
        )

    def test_single_source_ccds_invokes_loader(self) -> None:
        settings = _FakeSettings(xref_source="ccds")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 99
            mock_cls.return_value = mock_svc

            service = MainService(settings=settings)
            result = service.run()

        assert result.success is True
        assert result.record_count == 99
        assert result.source == "ccds"
        mock_cls.assert_called_once_with(
            source=XrefSource.CCDS, logger=service._logger
        )

    def test_unknown_source_returns_failed(self) -> None:
        settings = _FakeSettings(xref_source="does_not_exist")
        service = MainService(settings=settings)
        result = service.run()

        assert result.success is False
        assert result.status == LoadStatus.FAILED
        assert "Unknown XREF_SOURCE" in result.error
        assert result.source == "does_not_exist"

    def test_failing_loader_returns_failed_result(self) -> None:
        settings = _FakeSettings(xref_source="gene_info")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("network timeout")
            mock_cls.return_value = mock_svc

            service = MainService(settings=settings)
            result = service.run()

        assert result.success is False
        assert result.status == LoadStatus.FAILED
        assert "network timeout" in result.error

    def test_loader_exception_still_emits_failed_log(self) -> None:
        settings = _FakeSettings(xref_source="uniprot")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("disk full")
            mock_cls.return_value = mock_svc

            handler = logging.handlers.MemoryHandler(capacity=100)
            logger = logging.getLogger("hgnc_xref_loader")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            try:
                service = MainService(settings=settings)
                result = service.run()
            finally:
                logger.removeHandler(handler)

        error_logs = [
            r for r in handler.buffer if r.getMessage() == "main_service_failed"
        ]
        assert len(error_logs) == 1
        assert error_logs[0].__dict__.get("error") == "disk full"

    def test_success_emits_start_and_complete_logs(self) -> None:
        settings = _FakeSettings(xref_source="mane")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 42
            mock_cls.return_value = mock_svc

            handler = logging.handlers.MemoryHandler(capacity=100)
            logger = logging.getLogger("hgnc_xref_loader")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            try:
                service = MainService(settings=settings)
                result = service.run()
            finally:
                logger.removeHandler(handler)

        messages = [r.getMessage() for r in handler.buffer]
        assert "main_service_start" in messages
        assert "main_service_complete" in messages
        assert "main_service_failed" not in messages

    def test_complete_log_has_duration_and_record_count(self) -> None:
        settings = _FakeSettings(xref_source="agr")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 77
            mock_cls.return_value = mock_svc

            handler = logging.handlers.MemoryHandler(capacity=100)
            logger = logging.getLogger("hgnc_xref_loader")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            try:
                service = MainService(settings=settings)
                result = service.run()
            finally:
                logger.removeHandler(handler)

        complete_logs = [
            r
            for r in handler.buffer
            if r.getMessage() == "main_service_complete"
        ]
        assert len(complete_logs) == 1
        log_record = complete_logs[0]
        assert log_record.__dict__.get("record_count") == 77
        assert "duration_seconds" in log_record.__dict__

    def test_version_tracker_skips_when_unchanged(self) -> None:
        settings = _FakeSettings(xref_source="uniprot")
        mock_tracker = MagicMock()
        mock_tracker.should_skip.return_value = True

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            service = MainService(
                settings=settings, version_tracker=mock_tracker
            )
            result = service.run()

        assert result.status == LoadStatus.SKIPPED
        assert result.success is True
        mock_cls.return_value.run.assert_not_called()

    def test_version_tracker_proceeds_when_changed(self) -> None:
        settings = _FakeSettings(xref_source="uniprot")
        mock_tracker = MagicMock()
        mock_tracker.should_skip.return_value = False

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 33
            mock_cls.return_value = mock_svc

            service = MainService(
                settings=settings, version_tracker=mock_tracker
            )
            result = service.run()

        assert result.status == LoadStatus.SUCCESS
        assert result.record_count == 33

    def test_result_timestamps_are_set_on_success(self) -> None:
        settings = _FakeSettings(xref_source="uniprot")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.return_value = 1
            mock_cls.return_value = mock_svc

            service = MainService(settings=settings)
            result = service.run()

        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.finished_at >= result.started_at
        assert result.duration_seconds >= 0

    def test_result_timestamps_are_set_on_failure(self) -> None:
        settings = _FakeSettings(xref_source="uniprot")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("fail")
            mock_cls.return_value = mock_svc

            service = MainService(settings=settings)
            result = service.run()

        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.status == LoadStatus.FAILED

    def test_multiple_sequential_runs_independent(self) -> None:
        settings1 = _FakeSettings(xref_source="uniprot")
        settings2 = _FakeSettings(xref_source="ccds")

        with patch(
            "hgnc_xref_loader.services.main_service.XrefLoadService"
        ) as mock_cls:
            mock_svc1 = MagicMock()
            mock_svc1.run.return_value = 10
            mock_svc2 = MagicMock()
            mock_svc2.run.return_value = 20
            mock_cls.side_effect = [mock_svc1, mock_svc2]

            result1 = MainService(settings=settings1).run()
            result2 = MainService(settings=settings2).run()

        assert result1.record_count == 10
        assert result1.source == "uniprot"
        assert result2.record_count == 20
        assert result2.source == "ccds"
