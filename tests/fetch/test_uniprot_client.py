"""Tests for UniProt REST API streaming fetch client.

Validates the UniprotHttpClient: streaming TSV download, retry logic,
version header extraction, and error handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from hgnc_xref_loader.fetch.uniprot_client import (
    UniprotFetchError,
    UniprotHttpClient,
)


def _make_stream_context(data: bytes, version: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"X-UniProt-Release": version}
    mock_response.iter_bytes.return_value = [data]
    mock_response.raise_for_status.return_value = None
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_response)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


class TestUniprotHttpClientInit:
    """Test client initialisation and defaults."""

    def test_default_url(self) -> None:
        client = UniprotHttpClient()
        assert "rest.uniprot.org" in client.url

    def test_custom_url(self) -> None:
        client = UniprotHttpClient(url="https://example.com/test")
        assert client.url == "https://example.com/test"

    def test_default_max_retries(self) -> None:
        client = UniprotHttpClient()
        assert client.max_retries == 3

    def test_custom_max_retries(self) -> None:
        client = UniprotHttpClient(max_retries=5)
        assert client.max_retries == 5

    def test_default_timeout(self) -> None:
        client = UniprotHttpClient()
        assert client.timeout == 60


class TestUniprotFetchSuccess:
    """Test successful TSV fetch."""

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    def test_fetch_returns_bytes(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"X-UniProt-Release": "2024_03"}
        mock_response.iter_bytes.return_value = [b"header\n", b"data\n"]
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient()
        data, version = client.fetch()

        assert data == b"header\ndata\n"
        assert version == "2024_03"

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    def test_fetch_empty_version_header(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.iter_bytes.return_value = [b"data\n"]
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient()
        data, version = client.fetch()

        assert data == b"data\n"
        assert version == ""


class TestUniprotFetchRetries:
    """Test retry logic on transient errors."""

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    @patch("hgnc_xref_loader.fetch.uniprot_client.time.sleep")
    def test_retries_on_connect_error(
        self, mock_sleep: MagicMock, mock_client_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.side_effect = [
            httpx.ConnectError("refused"),
            _make_stream_context(b"ok\n", "2024_01"),
        ]
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient(max_retries=3)
        data, version = client.fetch()

        assert data == b"ok\n"
        assert mock_client.stream.call_count == 2

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    @patch("hgnc_xref_loader.fetch.uniprot_client.time.sleep")
    def test_retries_on_read_timeout(
        self, mock_sleep: MagicMock, mock_client_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.side_effect = [
            httpx.ReadTimeout("timeout"),
            _make_stream_context(b"ok\n", "2024_01"),
        ]
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient(max_retries=3)
        data, version = client.fetch()

        assert data == b"ok\n"

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    @patch("hgnc_xref_loader.fetch.uniprot_client.time.sleep")
    def test_exponential_backoff(
        self, mock_sleep: MagicMock, mock_client_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.side_effect = [
            httpx.ConnectError("err"),
            httpx.ConnectError("err"),
            _make_stream_context(b"ok\n", "2024_01"),
        ]
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient(max_retries=3)
        client.fetch()

        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    @patch("hgnc_xref_loader.fetch.uniprot_client.time.sleep")
    def test_raises_after_exhausted_retries(
        self, mock_sleep: MagicMock, mock_client_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.side_effect = httpx.ConnectError("down")
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient(max_retries=2)
        with pytest.raises(UniprotFetchError, match="Failed after 2 attempts"):
            client.fetch()


class TestUniprotFetchNonRetriable:
    """Test that non-retriable errors raise immediately."""

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    def test_http_status_error_raises_immediately(
        self, mock_client_cls: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient(max_retries=3)
        with pytest.raises(httpx.HTTPStatusError):
            client.fetch()


class TestUniprotVersionFetch:
    """Test standalone version fetch (separate endpoint)."""

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    def test_fetch_version_from_header(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"X-UniProt-Release": "2024_03"}
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient()
        version = client.fetch_version()

        assert version == "2024_03"

    @patch("hgnc_xref_loader.fetch.uniprot_client.httpx.Client")
    def test_fetch_version_url_is_search_endpoint(
        self, mock_client_cls: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"X-UniProt-Release": "2024_03"}
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = UniprotHttpClient()
        client.fetch_version()

        call_args = mock_client.get.call_args
        assert "search" in call_args[0][0]
        assert "P00750" in call_args[0][0]
