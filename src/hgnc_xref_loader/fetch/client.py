"""XrefFetchClient interface and default HTTP/file implementation.

Provides a mockable fetch abstraction that supports HTTP(S) downloads,
local file paths, transparent gzip decompression, and local file overrides
for offline debugging.
"""

from __future__ import annotations

import gzip
import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Raised when a fetch operation fails.

    Carries the URL/path and the underlying reason for diagnostic context.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Fetch failed for {url}: {reason}")


class XrefFetchClient(ABC):
    """Abstract fetch client for retrieving xref source data.

    Decouples adapters from direct HTTP/file access so tests can inject
    mocks or local fixtures without network calls.
    """

    @abstractmethod
    def fetch(self, url: str) -> bytes:
        """Fetch raw bytes from the given URL or file path.

        Args:
            url: HTTP(S) URL, ``file://`` URI, or local file path.

        Returns:
            Raw bytes of the fetched resource.

        Raises:
            FetchError: If the resource cannot be retrieved.
        """


class DefaultXrefFetchClient(XrefFetchClient):
    """Default fetch client supporting HTTP, local files, and gzip.

    Supports:
    - HTTP(S) URLs via ``urllib.request``
    - Local file paths (absolute or ``file://`` URIs)
    - Transparent gzip decompression for ``.gz`` files
    - Local file overrides mapping URLs to local paths for debugging

    Args:
        local_overrides: Mapping of URL to local file path. When a URL
            matches a key, the local file is returned instead.
    """

    def __init__(self, local_overrides: dict[str, str] | None = None) -> None:
        self._overrides = local_overrides or {}

    def fetch(self, url: str) -> bytes:
        if url in self._overrides:
            logger.info("Using local override for %s", url)
            return self._read_file(self._overrides[url])

        path = self._resolve_path(url)
        if path is not None:
            return self._read_file(str(path))

        return self._fetch_http(url)

    def _resolve_path(self, url: str) -> Path | None:
        if url.startswith("file://"):
            return Path(url[7:])
        if not url.startswith("http://") and not url.startswith("https://"):
            return Path(url)
        return None

    def _read_file(self, path: str) -> bytes:
        file_path = Path(path)
        if not file_path.exists():
            raise FetchError(path, "File not found")

        raw = file_path.read_bytes()
        if path.endswith(".gz"):
            return gzip.decompress(raw)
        return raw

    def _fetch_http(self, url: str) -> bytes:
        import urllib.request

        try:
            with urllib.request.urlopen(url) as resp:
                raw = resp.read()
        except Exception as exc:
            raise FetchError(url, str(exc)) from exc

        if url.endswith(".gz"):
            return gzip.decompress(raw)
        return raw
