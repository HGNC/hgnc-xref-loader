"""Tests for generic HTTP download client.

Validates the shared httpx-based client used by HTTP API xref loaders.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from hgnc_xref_loader.fetch.generic_http_client import (
    HttpDownloadClient,
    HttpDownloadError,
)


class TestHttpDownloadClientInit:
    """Test client initialisation."""

    def test_default_settings(self) -> None:
        client = HttpDownloadClient()
        assert client.timeout == 60
        assert client.max_retries == 3

    def test_custom_url(self) -> None:
        client = HttpDownloadClient(url="https://example.com/data.tsv")
        assert client.url == "https://example.com/data.tsv"


class TestHttpDownloadClientFetch:
    """Test HTTP GET download."""

    @patch("hgnc_xref_loader.fetch.generic_http_client.httpx.Client")
    def test_fetch_returns_bytes(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"col_a\tcol_b\n1\t2\n"
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = HttpDownloadClient(url="https://example.com/data.tsv")
        data = client.fetch()

        assert data == b"col_a\tcol_b\n1\t2\n"

    @patch("hgnc_xref_loader.fetch.generic_http_client.httpx.Client")
    @patch("hgnc_xref_loader.fetch.generic_http_client.time.sleep")
    def test_retries_on_connect_error(
        self, mock_sleep: MagicMock, mock_client_cls: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [
            httpx.ConnectError("refused"),
            mock_response,
        ]
        mock_client_cls.return_value = mock_client

        client = HttpDownloadClient(max_retries=3)
        data = client.fetch()

        assert data == b"data"
        assert mock_client.get.call_count == 2

    @patch("hgnc_xref_loader.fetch.generic_http_client.httpx.Client")
    @patch("hgnc_xref_loader.fetch.generic_http_client.time.sleep")
    def test_raises_after_exhausted_retries(
        self, mock_sleep: MagicMock, mock_client_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("down")
        mock_client_cls.return_value = mock_client

        client = HttpDownloadClient(max_retries=2)
        with pytest.raises(HttpDownloadError):
            client.fetch()

    @patch("hgnc_xref_loader.fetch.generic_http_client.httpx.Client")
    def test_fetch_with_params(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = HttpDownloadClient(url="https://example.com/api")
        client.fetch(params={"format": "tsv", "query": "human"})

        call_kwargs = mock_client.get.call_args
        assert call_kwargs[1].get("params") == {"format": "tsv", "query": "human"}
