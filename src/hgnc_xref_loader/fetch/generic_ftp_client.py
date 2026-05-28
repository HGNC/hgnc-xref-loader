"""Generic FTP download client for xref loader data sources.

Provides configurable FTP downloads with retries, exponential backoff,
and directory listing. Used by all FTP-based xref loaders (gene_info,
gene2refseq, rna_central, etc.).
"""

from __future__ import annotations

import ftplib
import logging
import time

logger = logging.getLogger(__name__)

DEFAULT_HOST = "ftp.ncbi.nlm.nih.gov"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
BACKOFF_BASE = 2


class FtpDownloadError(Exception):
    """Raised when an FTP download fails after all retries.

    Args:
        host: FTP server hostname.
        reason: Human-readable failure description.
    """

    def __init__(self, host: str, reason: str) -> None:
        self.host = host
        self.reason = reason
        super().__init__(f"FTP download failed for {host}: {reason}")


class FtpDownloadClient:
    """Generic FTP client for downloading files from remote servers.

    Supports passive mode, bounded retries with exponential backoff,
    and directory listing for discovering files.

    Args:
        host: FTP server hostname.
        remote_path: Default remote file path for fetch().
        timeout: Socket timeout in seconds.
        max_retries: Maximum retry attempts on transient errors.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        remote_path: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.host = host
        self.remote_path = remote_path
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch(self, remote_path: str | None = None) -> bytes:
        """Download a file from the FTP server.

        Args:
            remote_path: Override the default remote path.

        Returns:
            Raw bytes of the downloaded file.

        Raises:
            FtpDownloadError: If the download fails after all retries.
        """
        path = remote_path or self.remote_path
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._download(path)
            except ftplib.error_temp as exc:
                last_error = exc
                self._log_retry("temp_error", attempt, str(exc))
            except (socket.timeout, ConnectionError, OSError) as exc:
                last_error = exc
                self._log_retry("connection_error", attempt, str(exc))
            except ftplib.error_perm as exc:
                raise FtpDownloadError(host=self.host, reason=str(exc)) from exc

            if attempt < self.max_retries:
                delay = BACKOFF_BASE**attempt
                time.sleep(delay)

        raise FtpDownloadError(
            host=self.host,
            reason=f"Failed after {self.max_retries} attempts: {last_error}",
        )

    def list_files(self, directory: str, suffix: str | None = None) -> list[str]:
        """List files in a remote FTP directory.

        Args:
            directory: Remote directory path.
            suffix: Optional filename suffix to filter by.

        Returns:
            List of filenames, optionally filtered by suffix.
        """
        with ftplib.FTP() as ftp:
            ftp.connect(self.host, timeout=self.timeout)
            ftp.login()
            ftp.passive = True
            ftp.cwd(directory)
            files = ftp.nlst()

        if suffix:
            files = [f for f in files if f.endswith(suffix)]

        logger.info(
            "ftp_list_complete",
            extra={"directory": directory, "file_count": len(files)},
        )
        return files

    def _download(self, remote_path: str) -> bytes:
        """Perform a single FTP download attempt.

        Args:
            remote_path: Remote file path.

        Returns:
            Raw bytes of the file.
        """
        buf = bytearray()

        with ftplib.FTP() as ftp:
            ftp.connect(self.host, timeout=self.timeout)
            ftp.login()
            ftp.passive = True
            ftp.retrbinary(f"RETR {remote_path}", buf.extend)

        logger.info(
            "ftp_download_complete",
            extra={"host": self.host, "path": remote_path, "bytes": len(buf)},
        )
        return bytes(buf)

    def _log_retry(self, event: str, attempt: int, error: str) -> None:
        """Log a retriable failure.

        Args:
            event: Event label.
            attempt: Current attempt number.
            error: Error message.
        """
        logger.warning(
            event,
            extra={"event": event, "host": self.host, "attempt": attempt, "error": error},
        )
