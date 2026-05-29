"""Main service for the HGNC cross-reference loader.

Top-level orchestrator that reads configuration, resolves the requested
XrefSource from the loader registry, constructs an XrefLoadService with
injected dependencies, and invokes the loader lifecycle.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from hgnc_xref_loader.exceptions import ServiceError
from hgnc_xref_loader.loaders.registry import XrefSource
from hgnc_xref_loader.services.base_service import Service
from hgnc_xref_loader.services.xref_load_service import XrefLoadService

if TYPE_CHECKING:
    from shared.version_tracker import VersionTracker

    from hgnc_xref_loader.config import Settings


class LoadStatus(Enum):
    """Status of a loader run.

    Attributes:
        SUCCESS: Load completed normally.
        FAILED: Load encountered an error.
        SKIPPED: Load was skipped (version unchanged).
    """

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class MainServiceResult:
    """Outcome of a MainService run.

    Attributes:
        success: Whether the load completed without error.
        record_count: Number of records processed.
        error: Error message if the run failed.
        source: The XrefSource that was loaded.
        status: The LoadStatus of the run.
        started_at: Timestamp when the run started.
        finished_at: Timestamp when the run finished.
        duration_seconds: Wall-clock duration of the run.
    """

    success: bool = False
    record_count: int = 0
    error: str = ""
    source: str = ""
    status: LoadStatus = LoadStatus.FAILED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float = 0.0


class MainService(Service):
    """Orchestrate the HGNC cross-reference loading workflow.

    Reads XREF_SOURCE from settings, resolves the loader via the registry,
    constructs an XrefLoadService with injected dependencies, and invokes
    the loader lifecycle. Emits structured logs for start, completion,
    and failure with timestamps, duration, and status.

    Args:
        settings: Application configuration including XREF_SOURCE.
        version_tracker: Optional version tracker for skip gating.
    """

    def __init__(
        self,
        settings: "Settings",
        version_tracker: "VersionTracker | None" = None,
        ccds_post_load_service: object | None = None,
    ) -> None:
        self._settings = settings
        self._logger = logging.getLogger("hgnc_xref_loader")
        self._version_tracker = version_tracker
        self._ccds_post_load_service = ccds_post_load_service

    @classmethod
    def from_settings(cls, settings: "Settings") -> "MainService":
        """Construct a MainService from a Settings instance.

        Args:
            settings: Application configuration.

        Returns:
            A configured MainService ready to run.
        """
        return cls(settings=settings)

    def run(self) -> MainServiceResult:
        """Execute the cross-reference loading workflow.

        Returns:
            A ``MainServiceResult`` describing the outcome.
        """
        started_at = datetime.now()

        raw_source = self._settings.runtime.xref_source
        if not raw_source:
            return MainServiceResult(
                success=False,
                error="XREF_SOURCE is not configured",
                status=LoadStatus.FAILED,
                started_at=started_at,
                finished_at=datetime.now(),
            )

        try:
            source = XrefSource(raw_source)
        except ValueError:
            return MainServiceResult(
                success=False,
                error=f"Unknown XREF_SOURCE: {raw_source!r}",
                source=raw_source,
                status=LoadStatus.FAILED,
                started_at=started_at,
                finished_at=datetime.now(),
            )

        self._logger.info(
            "main_service_start",
            extra={"event": "main_service_start", "source": source.value},
        )

        if self._version_tracker is not None:
            table_name = source.value
            if self._version_tracker.should_skip(table_name, table_name):
                finished_at = datetime.now()
                self._logger.info(
                    "main_service_complete",
                    extra={
                        "event": "main_service_complete",
                        "source": source.value,
                        "status": LoadStatus.SKIPPED.value,
                        "duration_seconds": round(
                            (finished_at - started_at).total_seconds(), 3
                        ),
                    },
                )
                return MainServiceResult(
                    success=True,
                    source=source.value,
                    status=LoadStatus.SKIPPED,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=round(
                        (finished_at - started_at).total_seconds(), 3
                    ),
                )

        start_mono = time.monotonic()
        try:
            service = XrefLoadService(
                source=source,
                logger=self._logger,
                ccds_post_load_service=self._ccds_post_load_service
                if source == XrefSource.CCDS
                else None,
            )
            record_count = service.run()
        except Exception as exc:
            finished_at = datetime.now()
            elapsed = time.monotonic() - start_mono
            self._logger.error(
                "main_service_failed",
                extra={
                    "event": "main_service_failed",
                    "source": source.value,
                    "error": str(exc),
                    "duration_seconds": round(elapsed, 3),
                },
            )
            return MainServiceResult(
                success=False,
                error=str(exc),
                source=source.value,
                status=LoadStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=round(elapsed, 3),
            )

        finished_at = datetime.now()
        elapsed = time.monotonic() - start_mono
        self._logger.info(
            "main_service_complete",
            extra={
                "event": "main_service_complete",
                "source": source.value,
                "record_count": record_count,
                "duration_seconds": round(elapsed, 3),
            },
        )

        return MainServiceResult(
            success=True,
            record_count=record_count,
            source=source.value,
            status=LoadStatus.SUCCESS,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=round(elapsed, 3),
        )
