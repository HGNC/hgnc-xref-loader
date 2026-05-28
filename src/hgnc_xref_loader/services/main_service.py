"""Main service for the HGNC cross-reference loader.

Top-level orchestrator that reads configuration, resolves the requested
XrefSource from the loader registry, constructs an XrefLoadService with
injected dependencies, and invokes the loader lifecycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hgnc_xref_loader.exceptions import ServiceError
from hgnc_xref_loader.loaders.registry import XrefSource
from hgnc_xref_loader.services.base_service import Service
from hgnc_xref_loader.services.xref_load_service import XrefLoadService

if TYPE_CHECKING:
    from hgnc_xref_loader.config import Settings


@dataclass
class MainServiceResult:
    """Outcome of a MainService run.

    Attributes:
        success: Whether the load completed without error.
        record_count: Number of records processed.
        error: Error message if the run failed.
        source: The XrefSource that was loaded.
    """

    success: bool = False
    record_count: int = 0
    error: str = ""
    source: str = ""


class MainService(Service):
    """Orchestrate the HGNC cross-reference loading workflow.

    Reads XREF_SOURCE from settings, resolves the loader via the registry,
    constructs an XrefLoadService with injected dependencies, and invokes
    the loader lifecycle. Emits structured logs for start, completion,
    and failure.

    Args:
        settings: Application configuration including XREF_SOURCE.
    """

    def __init__(self, settings: "Settings") -> None:
        self._settings = settings
        self._logger = logging.getLogger("hgnc_xref_loader")

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
        raw_source = self._settings.runtime.xref_source
        if not raw_source:
            return MainServiceResult(
                success=False, error="XREF_SOURCE is not configured"
            )

        try:
            source = XrefSource(raw_source)
        except ValueError:
            return MainServiceResult(
                success=False,
                error=f"Unknown XREF_SOURCE: {raw_source!r}",
                source=raw_source,
            )

        self._logger.info(
            "main_service_start",
            extra={"event": "main_service_start", "source": source.value},
        )

        try:
            service = XrefLoadService(
                source=source,
                logger=self._logger,
            )
            record_count = service.run()
        except Exception as exc:
            self._logger.error(
                "main_service_failed",
                extra={
                    "event": "main_service_failed",
                    "source": source.value,
                    "error": str(exc),
                },
            )
            return MainServiceResult(
                success=False,
                error=str(exc),
                source=source.value,
            )

        self._logger.info(
            "main_service_complete",
            extra={
                "event": "main_service_complete",
                "source": source.value,
                "record_count": record_count,
            },
        )

        return MainServiceResult(
            success=True,
            record_count=record_count,
            source=source.value,
        )
