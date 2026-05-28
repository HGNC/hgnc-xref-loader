"""Tests for shared FTP download client.

Validates the generic FTP client that all FTP-based xref loaders share.
"""

from __future__ import annotations

import ftplib
import socket
from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.fetch.generic_ftp_client import (
    FtpDownloadClient,
    FtpDownloadError,
)


class TestFtpDownloadClientInit:
    """Test client initialisation."""

    def test_default_settings(self) -> None:
        client = FtpDownloadClient()
        assert client.host == "ftp.ncbi.nlm.nih.gov"
        assert client.timeout == 30
        assert client.max_retries == 3

    def test_custom_host(self) -> None:
        client = FtpDownloadClient(host="ftp.ebi.ac.uk")
        assert client.host == "ftp.ebi.ac.uk"


class TestFtpDownloadClientFetch:
    """Test FTP download with retries."""

    @patch("hgnc_xref_loader.fetch.generic_ftp_client.ftplib.FTP")
    def test_fetch_returns_bytes(self, mock_ftp_cls: MagicMock) -> None:
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = FtpDownloadClient(host="test.host", remote_path="/pub/test.txt")
        data = client.fetch()

        assert isinstance(data, bytes)
        mock_ftp.retrbinary.assert_called_once()

    @patch("hgnc_xref_loader.fetch.generic_ftp_client.time.sleep")
    @patch("hgnc_xref_loader.fetch.generic_ftp_client.ftplib.FTP")
    def test_retries_on_transient_error(
        self, mock_ftp_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ftp.retrbinary.side_effect = [
            ftplib.error_temp("421"),
            None,
        ]

        client = FtpDownloadClient(max_retries=3)
        data = client.fetch()
        assert isinstance(data, bytes)
        assert mock_ftp.retrbinary.call_count == 2

    @patch("hgnc_xref_loader.fetch.generic_ftp_client.time.sleep")
    @patch("hgnc_xref_loader.fetch.generic_ftp_client.ftplib.FTP")
    def test_raises_after_exhausted_retries(
        self, mock_ftp_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ftp.retrbinary.side_effect = ftplib.error_temp("421")

        client = FtpDownloadClient(max_retries=2)
        with pytest.raises(FtpDownloadError):
            client.fetch()


class TestFtpDownloadClientListFiles:
    """Test FTP directory listing."""

    @patch("hgnc_xref_loader.fetch.generic_ftp_client.ftplib.FTP")
    def test_list_files_returns_filenames(self, mock_ftp_cls: MagicMock) -> None:
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ftp.nlst.return_value = ["file1.txt", "file2.gz", "README"]

        client = FtpDownloadClient()
        files = client.list_files("/pub/dir")
        assert files == ["file1.txt", "file2.gz", "README"]

    @patch("hgnc_xref_loader.fetch.generic_ftp_client.ftplib.FTP")
    def test_list_files_with_pattern(self, mock_ftp_cls: MagicMock) -> None:
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ftp.nlst.return_value = ["gene_info.gz", "gene_history.gz", "README"]

        client = FtpDownloadClient()
        files = client.list_files("/pub/dir", suffix=".gz")
        assert files == ["gene_info.gz", "gene_history.gz"]
