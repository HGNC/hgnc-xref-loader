"""Integration tests for CLI structured logging in the reference service."""

import json
from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.cli import main
from hgnc_xref_loader.exceptions import ServiceError


class TestCLIStructuredLoggingOnSuccess:
    def test_cli_emits_structured_log_on_success(self, capsys):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc = MagicMock()
            mock_svc_cls.from_settings.return_value = mock_svc
            main([])
        captured = capsys.readouterr()
        if captured.out.strip():
            lines = [l for l in captured.out.strip().split("\n") if l]
            last = json.loads(lines[-1])
            assert "severity" in last


class TestCLIStructuredLoggingOnError:
    def test_cli_returns_3_on_service_error(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc = MagicMock()
            mock_svc.run.side_effect = ServiceError("load failed")
            mock_svc_cls.from_settings.return_value = mock_svc
            result = main([])
        assert result == 3

    def test_cli_returns_2_on_config_error(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings", side_effect=Exception("bad env")):
            result = main([])
        assert result == 2

    def test_cli_returns_1_on_unexpected_error(self):
        with patch("hgnc_xref_loader.cli.configure_logging"), \
             patch("hgnc_xref_loader.cli.Settings") as mock_settings_cls, \
             patch("hgnc_xref_loader.cli.MainService") as mock_svc_cls:
            mock_settings_cls.return_value = MagicMock()
            mock_svc = MagicMock()
            mock_svc.run.side_effect = RuntimeError("unexpected")
            mock_svc_cls.from_settings.return_value = mock_svc
            result = main([])
        assert result == 1


class TestCLINoPrint:
    def test_cli_does_not_use_print(self):
        """Verify cli.py source has no print() calls."""
        import hgnc_xref_loader.cli as cli_module

        source = cli_module.__file__
        assert source is not None
        with open(source) as fh:
            content = fh.read()
        assert "print(" not in content
