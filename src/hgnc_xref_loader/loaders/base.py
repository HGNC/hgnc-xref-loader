"""Abstract base class for all xref loader implementations.

Defines the template method lifecycle: fetch_and_parse() -> normalize() -> sort,
with automatic metrics tracking, structured logging, and dependency injection
for fetch clients and staging repositories.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from hgnc_xref_loader.domain.models import LoaderMetrics, XrefRecord

if TYPE_CHECKING:
    from hgnc_xref_loader.fetch.client import XrefFetchClient
    from hgnc_xref_loader.repositories.xref_staging_repository import (
        XrefStagingRepository,
    )


class BaseXrefLoader(ABC):
    """Abstract base class for HGNC cross-reference loader implementations.

    Each concrete loader handles a single XREF_SOURCE, implementing the
    fetch-transform-load lifecycle. Loaders receive optional dependencies
    through constructor injection.

    The ``run()`` method is a template method that orchestrates
    ``fetch_and_parse()``, ``normalize()``, and returns sorted records.
    Metrics are tracked automatically.

    Args:
        fetch_client: Optional fetch client for retrieving source data.
        staging_repo: Optional staging repository for persistence.
        logger: Optional logger; defaults to module-level logger.
    """

    def __init__(
        self,
        fetch_client: XrefFetchClient | None = None,
        staging_repo: XrefStagingRepository | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._fetch_client = fetch_client
        self._staging_repo = staging_repo
        self._logger = logger or logging.getLogger(__name__)
        self.metrics = LoaderMetrics(source=self._source_name())

    def run(self) -> int:
        """Execute the complete loader lifecycle.

        Orchestrates fetch_and_parse(), normalize(), sorts the output for
        deterministic ordering, and updates metrics.

        Returns:
            The number of normalised records produced.
        """
        raw = self.fetch_and_parse()
        self.metrics.total_rows = len(raw)

        normalized = self.normalize(raw)
        normalized.sort()
        self.metrics.parsed_rows = len(normalized)
        self.metrics.skipped_rows = self.metrics.total_rows - self.metrics.parsed_rows

        self._logger.info(
            "loader_run_complete",
            extra={
                "event": "loader_run_complete",
                "source": self.metrics.source,
                "total": self.metrics.total_rows,
                "parsed": self.metrics.parsed_rows,
                "skipped": self.metrics.skipped_rows,
            },
        )

        return len(normalized)

    def _source_name(self) -> str:
        return self.__class__.__name__.replace("XrefLoader", "").replace("Loader", "").lower()

    @abstractmethod
    def fetch_and_parse(self) -> list[dict]:
        """Fetch raw data from the external source and parse into records.

        Returns:
            A list of raw dictionaries representing parsed source data.
        """

    @abstractmethod
    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        """Transform raw parsed records into normalised XrefRecord models.

        Args:
            raw: Raw dictionaries from fetch_and_parse().

        Returns:
            A list of validated XrefRecord instances ready for persistence.
        """
