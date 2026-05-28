"""FTP client for fetching CCDS data from the NCBI FTP server.

Downloads CCDS.current.txt with configurable host, path, timeouts,
and bounded retries with exponential backoff. All FTP interactions are
scoped to this module so the rest of the codebase stays FTP-agnostic.
"""

from __future__ import annotations

import ftplib
import logging
import socket
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_HOST = "ftp.ncbi.nlm.nih.gov"
DEFAULT_REMOTE_PATH = "/pub/CCDS/current_human/CCDS.current.txt"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
BACKOFF_BASE = 2


class FtpFetchError(Exception):
    """Raised when an FTP fetch operation fails after all retries.

    Carries the host and a human-readable reason for diagnostic context.

    Args:
        host: FTP server hostname.
        reason: Description of the failure.
    """

    def __init__(self, host: str, reason: str) -> None:
        self.host = host
        self.reason = reason
        super().__init__(f"FTP fetch failed for {host}: {reason}")


class CcdsFtpClient:
    """FTP client for downloading CCDS.current.txt from NCBI.

    Connects to the NCBI FTP server in passive mode, downloads the CCDS
    file into memory, and returns the raw bytes. Retries transient errors
    (4xx FTP responses, socket timeouts) with exponential backoff.

    Args:
        host: FTP server hostname.
        remote_path: Full path to the CCDS file on the server.
        timeout: Socket timeout in seconds.
        max_retries: Maximum number of retry attempts.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        remote_path: str = DEFAULT_REMOTE_PATH,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.host = host
        self.remote_path = remote_path
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch(self) -> bytes:
        """Download the CCDS file from the FTP server.

        Returns:
            Raw bytes of the downloaded file.

        Raises:
            FtpFetchError: If the download fails after all retries.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._download()
            except ftplib.error_temp as exc:
                last_error = exc
                logger.warning(
                    "ftp_transient_error",
                    extra={
                        "event": "ftp_transient_error",
                        "host": self.host,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
            except (socket.timeout, ConnectionError, OSError) as exc:
                last_error = exc
                logger.warning(
                    "ftp_connection_error",
                    extra={
                        "event": "ftp_connection_error",
                        "host": self.host,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
            except ftplib.error_perm as exc:
                raise FtpFetchError(host=self.host, reason=str(exc)) from exc

            if attempt < self.max_retries:
                delay = BACKOFF_BASE**attempt
                logger.info(
                    "ftp_retry",
                    extra={
                        "event": "ftp_retry",
                        "host": self.host,
                        "attempt": attempt,
                        "delay": delay,
                    },
                )
                time.sleep(delay)

        raise FtpFetchError(
            host=self.host,
            reason=f"Failed after {self.max_retries} attempts: {last_error}",
        )

    def _download(self) -> bytes:
        """Perform a single FTP download attempt.

        Returns:
            Raw bytes of the downloaded file.

        Raises:
            ftplib.error_temp: On transient FTP errors (retriable).
            ftplib.error_perm: On permanent FTP errors (not retriable).
            socket.timeout: On connection timeout.
            ConnectionError: On connection failure.
        """
        buf = bytearray()

        with ftplib.FTP() as ftp:
            ftp.connect(self.host, timeout=self.timeout)
            ftp.login()
            ftp.passive = True
            ftp.retrbinary(f"RETR {self.remote_path}", buf.extend)

        logger.info(
            "ftp_download_complete",
            extra={
                "event": "ftp_download_complete",
                "host": self.host,
                "path": self.remote_path,
                "bytes": len(buf),
            },
        )

        return bytes(buf)
