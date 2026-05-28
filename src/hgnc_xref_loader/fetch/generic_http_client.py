"""Generic HTTP download client for xref loader data sources.

Provides configurable HTTP GET downloads with retries and exponential
backoff. Used by all HTTP-based xref loaders (gencc, iuphar, omim,
rgd_orthologs, etc.).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 3
BACKOFF_BASE = 2


class HttpDownloadError(Exception):
    """Raised when an HTTP download fails after all retries.

    Args:
        url: The URL that failed.
        reason: Human-readable failure description.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"HTTP download failed for {url}: {reason}")


class HttpDownloadClient:
    """Generic HTTP client for downloading data via GET requests.

    Supports configurable timeouts, bounded retries with exponential
    backoff on transient errors, and optional query parameters.

    Args:
        url: Target URL for GET requests.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts on transient errors.
    """

    def __init__(
        self,
        url: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch(
        self,
        url: str | None = None,
        params: dict[str, str] | None = None,
    ) -> bytes:
        """Download data via HTTP GET.

        Args:
            url: Override the default URL.
            params: Optional query parameters.

        Returns:
            Raw response bytes.

        Raises:
            HttpDownloadError: If the download fails after all retries.
            httpx.HTTPStatusError: On non-retriable HTTP status errors.
        """
        target = url or self.url
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._get(target, params)
            except httpx.ConnectError as exc:
                last_error = exc
                self._log_retry("connect_error", attempt, str(exc))
            except httpx.ReadTimeout as exc:
                last_error = exc
                self._log_retry("read_timeout", attempt, str(exc))

            if attempt < self.max_retries:
                time.sleep(BACKOFF_BASE**attempt)

        raise HttpDownloadError(
            url=target,
            reason=f"Failed after {self.max_retries} attempts: {last_error}",
        )

    def _get(self, url: str, params: dict[str, str] | None) -> bytes:
        """Perform a single GET request.

        Args:
            url: Target URL.
            params: Optional query parameters.

        Returns:
            Response content bytes.
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        logger.info(
            "http_download_complete",
            extra={"url": url, "bytes": len(response.content)},
        )
        return response.content

    def _log_retry(self, event: str, attempt: int, error: str) -> None:
        """Log a retriable failure.

        Args:
            event: Event label.
            attempt: Current attempt number.
            error: Error message.
        """
        logger.warning(
            event,
            extra={"event": event, "attempt": attempt, "error": error},
        )
