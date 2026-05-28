"""HTTP client for streaming UniProt TSV data from the REST API.

Downloads the active human proteome TSV stream with bounded retries
and exponential backoff on transient failures. Extracts the
``X-UniProt-Release`` header for version tracking.

Uses httpx for HTTP/2 streaming support.
"""

from __future__ import annotations

import logging
import time

import httpx

from hgnc_xref_loader.loaders.uniprot_schemas import UNIPROT_REST_URL

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 3
BACKOFF_BASE = 2
VERSION_QUERY_URL = (
    "https://rest.uniprot.org/uniprotkb/search?query=accession_id:P00750"
)


class UniprotFetchError(Exception):
    """Raised when a UniProt fetch operation fails after all retries.

    Args:
        url: The URL that failed.
        reason: Human-readable description of the failure.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"UniProt fetch failed for {url}: {reason}")


class UniprotHttpClient:
    """Streaming HTTP client for the UniProt REST API.

    Downloads the full human proteome TSV via the streaming endpoint and
    extracts the ``X-UniProt-Release`` version header. Retries transient
    connection errors with exponential backoff.

    Args:
        url: Full URL for the UniProt TSV stream.
        max_retries: Maximum number of retry attempts on transient errors.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        url: str = UNIPROT_REST_URL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.url = url
        self.max_retries = max_retries
        self.timeout = timeout

    def fetch(self) -> tuple[bytes, str]:
        """Stream the UniProt TSV and extract the version header.

        Returns:
            A tuple of ``(raw_tsv_bytes, version_string)``.

        Raises:
            UniprotFetchError: If the fetch fails after all retries.
            httpx.HTTPStatusError: On non-retriable HTTP errors.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._stream()
            except httpx.ConnectError as exc:
                last_error = exc
                self._log_retry("connect_error", attempt, str(exc))
            except httpx.ReadTimeout as exc:
                last_error = exc
                self._log_retry("read_timeout", attempt, str(exc))

            if attempt < self.max_retries:
                delay = BACKOFF_BASE**attempt
                logger.info(
                    "uniprot_retry",
                    extra={
                        "event": "uniprot_retry",
                        "attempt": attempt,
                        "delay": delay,
                    },
                )
                time.sleep(delay)

        raise UniprotFetchError(
            url=self.url,
            reason=f"Failed after {self.max_retries} attempts: {last_error}",
        )

    def fetch_version(self) -> str:
        """Fetch the UniProt release version via a lightweight query.

        Issues a single-record search and reads the
        ``X-UniProt-Release`` response header.

        Returns:
            The UniProt release version string (e.g. ``"2024_03"``).
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(VERSION_QUERY_URL)
            response.raise_for_status()
            return response.headers.get("X-UniProt-Release", "")

    def _stream(self) -> tuple[bytes, str]:
        """Perform a single streaming download attempt.

        Returns:
            A tuple of ``(raw_tsv_bytes, version_string)``.

        Raises:
            httpx.ConnectError: On connection failure (retriable).
            httpx.ReadTimeout: On read timeout (retriable).
            httpx.HTTPStatusError: On non-retriable HTTP status errors.
        """
        chunks: list[bytes] = []

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("GET", self.url) as response:
                response.raise_for_status()
                version = response.headers.get("X-UniProt-Release", "")
                for chunk in response.iter_bytes():
                    chunks.append(chunk)

        data = b"".join(chunks)
        logger.info(
            "uniprot_download_complete",
            extra={
                "event": "uniprot_download_complete",
                "bytes": len(data),
                "version": version,
            },
        )
        return data, version

    def _log_retry(self, event: str, attempt: int, error: str) -> None:
        """Emit a warning log for a retriable failure.

        Args:
            event: Event label for structured logging.
            attempt: Current attempt number (1-indexed).
            error: Error message string.
        """
        logger.warning(
            event,
            extra={
                "event": event,
                "attempt": attempt,
                "error": error,
            },
        )
