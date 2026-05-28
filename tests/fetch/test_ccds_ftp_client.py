"""Tests for the CCDS FTP fetcher.

Validates the FTP client that downloads CCDS.current.txt from the NCBI FTP
server with robust error handling, retries, and configurability.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.exceptions import ServiceError


class TestCcdsFtpClientImports:
    """Verify the module and class can be imported."""

    def test_import_ccds_ftp_client(self) -> None:
        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        assert CcdsFtpClient is not None


class TestCcdsFtpClientInit:
    """Verify constructor configuration and defaults."""

    def test_default_host_and_path(self) -> None:
        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        client = CcdsFtpClient()
        assert "ncbi.nlm.nih.gov" in client.host
        assert "CCDS.current.txt" in client.remote_path

    def test_custom_host_and_path(self) -> None:
        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        client = CcdsFtpClient(host="ftp.example.com", remote_path="/data/test.txt")
        assert client.host == "ftp.example.com"
        assert client.remote_path == "/data/test.txt"

    def test_default_timeout(self) -> None:
        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        client = CcdsFtpClient()
        assert client.timeout > 0

    def test_default_max_retries(self) -> None:
        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        client = CcdsFtpClient()
        assert client.max_retries >= 1


class TestCcdsFtpClientFetch:
    """Verify successful FTP download."""

    @patch("hgnc_xref_loader.fetch.ftp_client.ftplib.FTP")
    def test_fetch_returns_bytes(self, mock_ftp_cls: MagicMock) -> None:
        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        captured_buf = io.BytesIO()

        def fake_retrbinary(cmd: str, callback: object) -> None:
            callback(b"line1\n")
            callback(b"line2\n")

        mock_ftp.retrbinary = fake_retrbinary

        client = CcdsFtpClient(host="ftp.example.com", remote_path="/data/CCDS.current.txt")
        result = client.fetch()

        assert isinstance(result, bytes)
        assert b"line1" in result
        assert b"line2" in result

    @patch("hgnc_xref_loader.fetch.ftp_client.ftplib.FTP")
    def test_fetch_uses_correct_paths(self, mock_ftp_cls: MagicMock) -> None:
        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ftp.retrbinary = MagicMock()

        client = CcdsFtpClient(host="ftp.example.com", remote_path="/pub/CCDS.current.txt")
        client.fetch()

        mock_ftp.login.assert_called_once_with()
        mock_ftp.retrbinary.assert_called_once()
        cmd = mock_ftp.retrbinary.call_args[0][0]
        assert "RETR /pub/CCDS.current.txt" == cmd


class TestCcdsFtpClientErrors:
    """Verify error handling for connection and download failures."""

    @patch("hgnc_xref_loader.fetch.ftp_client.ftplib.FTP")
    def test_connection_failure_raises_service_error(self, mock_ftp_cls: MagicMock) -> None:
        import ftplib

        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient, FtpFetchError

        mock_ftp_cls.return_value.__enter__ = MagicMock(
            side_effect=ftplib.error_temp("Connection refused")
        )
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = CcdsFtpClient(host="ftp.bad.com", max_retries=1)

        with pytest.raises(FtpFetchError, match="ftp.bad.com"):
            client.fetch()

    @patch("hgnc_xref_loader.fetch.ftp_client.ftplib.FTP")
    def test_file_not_found_raises_ftp_error(self, mock_ftp_cls: MagicMock) -> None:
        import ftplib

        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient, FtpFetchError

        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ftp.retrbinary = MagicMock(
            side_effect=ftplib.error_perm("550 File not found")
        )

        client = CcdsFtpClient(host="ftp.example.com", max_retries=1)

        with pytest.raises(FtpFetchError):
            client.fetch()

    @patch("hgnc_xref_loader.fetch.ftp_client.ftplib.FTP")
    def test_timeout_raises_ftp_error(self, mock_ftp_cls: MagicMock) -> None:
        import socket

        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient, FtpFetchError

        mock_ftp_cls.return_value.__enter__ = MagicMock(
            side_effect=socket.timeout("timed out")
        )
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = CcdsFtpClient(host="ftp.slow.com", max_retries=1)

        with pytest.raises(FtpFetchError, match="timed out"):
            client.fetch()


class TestCcdsFtpClientRetries:
    """Verify retry logic with exponential backoff."""

    @patch("hgnc_xref_loader.fetch.ftp_client.time.sleep")
    @patch("hgnc_xref_loader.fetch.ftp_client.ftplib.FTP")
    def test_retries_on_transient_failure(self, mock_ftp_cls: MagicMock, mock_sleep: MagicMock) -> None:
        import ftplib

        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient

        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def retrbinary_with_transient_failure(cmd: str, callback: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ftplib.error_temp("421 Connection closed")
            callback(b"success\n")

        mock_ftp.retrbinary = retrbinary_with_transient_failure

        client = CcdsFtpClient(host="ftp.example.com", max_retries=3)
        result = client.fetch()

        assert result == b"success\n"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("hgnc_xref_loader.fetch.ftp_client.time.sleep")
    @patch("hgnc_xref_loader.fetch.ftp_client.ftplib.FTP")
    def test_exhausts_retries_raises_error(self, mock_ftp_cls: MagicMock, mock_sleep: MagicMock) -> None:
        import ftplib

        from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient, FtpFetchError

        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ftp.retrbinary = MagicMock(
            side_effect=ftplib.error_temp("421 Connection closed")
        )

        client = CcdsFtpClient(host="ftp.example.com", max_retries=2)

        with pytest.raises(FtpFetchError):
            client.fetch()

        assert mock_sleep.call_count == 1
