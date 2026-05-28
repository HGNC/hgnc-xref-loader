"""MANE load service.

Orchestrates the NCBI MANE summary load pipeline.

The version is resolved dynamically from the MANE README_versions.txt
to construct the correct download URL.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.mane_parser import ManeParser

logger = logging.getLogger(__name__)

MANE_BASE_URL = "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/current/"
VERSION_URL = MANE_BASE_URL + "README_versions.txt"
MANE_TABLE = "mane"
MANE_STAGING = "mane_update"
MANE_VERSION_RE = re.compile(r"MANE\s+Version\s+(\d+\.\d+)")


@dataclass
class ManeLoadResult:
    """Outcome of a MANE load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class ManeLoadService:
    """Orchestrate the NCBI MANE load pipeline.

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
        self._parser = ManeParser()

    def run(self) -> ManeLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``ManeLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                MANE_TABLE, self._source_version
            ):
                return ManeLoadResult(success=True, skipped=True)

            version = self._resolve_version()
            mane_url = (
                f"{MANE_BASE_URL}"
                f"MANE.GRCh38.v{version}.summary.txt.gz"
            )

            data = self._http_client.fetch(url=mane_url)

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(MANE_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                MANE_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                MANE_STAGING, MANE_TABLE
            )

            self._version_tracker.record_version(
                MANE_TABLE, self._source_version
            )

            logger.info(
                "mane_load_complete",
                extra={"rows_loaded": count},
            )

            return ManeLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "mane_load_failed",
                extra={"error": str(exc)},
            )
            return ManeLoadResult(success=False, error=str(exc))

    def _resolve_version(self) -> str:
        """Resolve the current MANE version from the README.

        Returns:
            MANE version string (e.g. '1.4').
        """
        readme = self._http_client.fetch(url=VERSION_URL)
        match = MANE_VERSION_RE.search(readme.decode("utf-8", errors="replace"))
        if not match:
            msg = "Could not find MANE version in README_versions.txt"
            raise ValueError(msg)
        return match.group(1)
