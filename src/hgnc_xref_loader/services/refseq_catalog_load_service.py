"""RefSeq catalog load service.

Orchestrates the NCBI RefSeq catalog load pipeline: HTTP download, gzip
decompression, parsing, staging, and promotion.

The URL is dynamically resolved by listing the NCBI release-catalog
directory and selecting the latest ``RefSeq-release*.catalog.gz`` file.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.refseq_catalog_parser import RefseqCatalogParser

logger = logging.getLogger(__name__)

REFSEQ_CATALOG_DIR = (
    "https://ftp.ncbi.nlm.nih.gov/refseq/release/release-catalog/"
)
CATALOG_PATTERN = re.compile(r"(RefSeq-release\d+\.catalog\.gz)")
REFSEQ_CATALOG_TABLE = "refseq_catalog"
REFSEQ_CATALOG_STAGING = "refseq_catalog_update"


@dataclass
class RefseqCatalogLoadResult:
    """Outcome of a refseq_catalog load run.

    Attributes:
        success: Whether the load completed without error.
        skipped: Whether the load was skipped (version unchanged).
        rows_loaded: Number of rows loaded into staging.
        error: Error message if the load failed.
    """

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class RefseqCatalogLoadService:
    """Orchestrate the NCBI RefSeq catalog load pipeline.

    Args:
        http_client: HTTP download client.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current source version string.
    """

    def __init__(
        self,
        http_client: Any,
        staging_repo: Any,
        version_tracker: Any,
        source_version: str = "",
    ) -> None:
        self._http_client = http_client
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._source_version = source_version
        self._parser = RefseqCatalogParser()

    def run(self) -> RefseqCatalogLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``RefseqCatalogLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                REFSEQ_CATALOG_TABLE, self._source_version
            ):
                return RefseqCatalogLoadResult(success=True, skipped=True)

            catalog_url = self._resolve_catalog_url()
            data = self._http_client.fetch(url=catalog_url)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(REFSEQ_CATALOG_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                REFSEQ_CATALOG_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                REFSEQ_CATALOG_STAGING, REFSEQ_CATALOG_TABLE
            )

            self._version_tracker.record_version(
                REFSEQ_CATALOG_TABLE, self._source_version
            )

            logger.info(
                "refseq_catalog_load_complete",
                extra={"rows_loaded": count},
            )

            return RefseqCatalogLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "refseq_catalog_load_failed",
                extra={"error": str(exc)},
            )
            return RefseqCatalogLoadResult(success=False, error=str(exc))

    def _resolve_catalog_url(self) -> str:
        """Resolve the latest RefSeq catalog file URL.

        Returns:
            Full URL to the latest ``RefSeq-release*.catalog.gz``.
        """
        listing = self._http_client.fetch(url=REFSEQ_CATALOG_DIR)
        match = CATALOG_PATTERN.search(listing.decode("utf-8", errors="replace"))
        if not match:
            msg = "Could not find RefSeq-release*.catalog.gz in directory listing"
            raise ValueError(msg)
        return REFSEQ_CATALOG_DIR + match.group(1)
