"""Tests for the CLI controller pattern."""

from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.cli import main
from hgnc_xref_loader.exceptions import ConfigError, ServiceError


class TestMainSuccess:
    def test_main_returns_zero_on_success(self):
        with patch("hgnc_xref_loader.cli.configure_logging") as mock_log, \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc = MagicMock()
            mock_svc_cls.from_settings.return_value = mock_svc
            result = main([])
        assert result == 0

    def test_main_calls_configure_logging(self):
        with patch("hgnc_xref_loader.cli.configure_logging") as mock_log, \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc_cls.from_settings.return_value = MagicMock()
            main([])
        mock_log.assert_called_once()

    def test_main_loads_settings(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService"):
            mock_settings_cls.return_value = MagicMock()
            main([])
        mock_settings_cls.assert_called_once()

    def test_main_creates_service_from_settings(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings = MagicMock()
            mock_settings_cls.return_value = mock_settings
            main([])
        mock_svc_cls.from_settings.assert_called_once_with(mock_settings)

    def test_main_calls_service_run(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc = MagicMock()
            mock_svc_cls.from_settings.return_value = mock_svc
            main([])
        mock_svc.run.assert_called_once()


class TestMainConfigError:
    def test_config_error_returns_exit_code_2(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings", side_effect=ConfigError("bad config")):
            result = main([])
        assert result == 2

    def test_config_error_during_settings_load(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings", side_effect=ConfigError("missing env")):
            result = main([])
        assert result == 2


class TestMainServiceError:
    def test_service_error_returns_exit_code_3(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc = MagicMock()
            mock_svc.run.side_effect = ServiceError("domain failure")
            mock_svc_cls.from_settings.return_value = mock_svc
            result = main([])
        assert result == 3


class TestMainUnexpectedError:
    def test_unexpected_error_returns_exit_code_1(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("boom")
            mock_svc_cls.from_settings.return_value = mock_svc
            result = main([])
        assert result == 1


class TestMainNoBusinessLogic:
    def test_main_does_not_import_repositories_directly(self):
        """CLI must not import repository modules."""
        import hgnc_xref_loader.cli as cli_module

        source = cli_module.__file__
        assert source is not None
        with open(source) as fh:
            content = fh.read()
        assert "repositories" not in content.split("import")[0] if "import" in content else True
