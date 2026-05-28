"""XrefLoadService orchestrates the cross-reference loader lifecycle.

Resolves the configured XrefSource to a concrete loader via the registry,
instantiates and runs the loader, and emits structured metrics and log
events for job start, completion, and failure.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.exceptions import (
    LoaderRuntimeError,
    UnknownSourceError,
)
from hgnc_xref_loader.loaders.registry import XrefSource, get_loader

if TYPE_CHECKING:
    from hgnc_xref_loader.repositories.xref_staging_repository import (
        XrefStagingRepository,
    )


class XrefLoadService:
    """Orchestrate the cross-reference loader lifecycle for a single source.

    Accepts a configured source enum value and a logger, resolves the
    concrete loader class through the registry, and invokes its ``run()``
    method. Emits structured log events and measures per-run metrics
    including record count and elapsed duration.

    Args:
        source: The XrefSource enum value identifying which loader to run.
        logger: Logger instance for emitting structured events.

    Raises:
        UnknownSourceError: When no loader is registered for the source.
        LoaderRuntimeError: When the loader fails during execution.
    """

    def __init__(
        self,
        source: XrefSource,
        logger: logging.Logger,
        staging_repository: XrefStagingRepository | None = None,
    ) -> None:
        self.source = source
        self._logger = logger
        self._staging_repository = staging_repository

    def run(self) -> int:
        """Resolve and execute the loader for the configured source.

        Returns:
            The number of records processed by the loader.

        Raises:
            UnknownSourceError: If no loader is registered for the source.
            LoaderRuntimeError: If the loader raises during execution.
        """
        loader_cls = get_loader(self.source)
        loader = loader_cls()

        self._logger.info(
            "loader_start",
            extra={
                "event": "loader_start",
                "source": self.source.value,
            },
        )

        start = time.monotonic()
        try:
            record_count = loader.run()
        except (UnknownSourceError, LoaderRuntimeError):
            raise
        except Exception as exc:
            raise LoaderRuntimeError(
                f"Loader {self.source.value!r} failed: {exc}"
            ) from exc
        finally:
            elapsed = time.monotonic() - start

        self._logger.info(
            "loader_complete",
            extra={
                "event": "loader_complete",
                "source": self.source.value,
                "record_count": record_count,
                "duration_seconds": round(elapsed, 3),
            },
        )

        return record_count
