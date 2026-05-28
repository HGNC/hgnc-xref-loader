"""CCDS Sequence load service.

Orchestrates the NCBI CCDS sequence load pipeline: FTP download, gzip
decompression, FASTA parsing, staging, and promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.ccds_seq_parser import CcdsSeqParser

logger = logging.getLogger(__name__)

CCDS_SEQ_TABLE = "ccds_seq"
CCDS_SEQ_STAGING = "ccds_seq_update"


@dataclass
class CcdsSeqLoadResult:
    """Outcome of a ccds_seq load run.

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


class CcdsSeqLoadService:
    """Orchestrate the NCBI CCDS sequence load pipeline.

    Args:
        ftp_client: FTP download client for NCBI.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current source version string.
    """

    def __init__(
        self,
        ftp_client: Any,
        staging_repo: Any,
        version_tracker: Any,
        source_version: str = "",
    ) -> None:
        self._ftp_client = ftp_client
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._source_version = source_version
        self._parser = CcdsSeqParser()

    def run(self) -> CcdsSeqLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``CcdsSeqLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                CCDS_SEQ_TABLE, self._source_version
            ):
                return CcdsSeqLoadResult(success=True, skipped=True)

            data = self._ftp_client.fetch()

            records = self._parser.parse(data)

            self._staging_repo.prepare_staging_table(CCDS_SEQ_TABLE)

            staging_dicts = [r.to_staging_dict() for r in records]
            count = self._staging_repo.bulk_copy_into_staging(
                CCDS_SEQ_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                CCDS_SEQ_STAGING, CCDS_SEQ_TABLE
            )

            self._version_tracker.record_version(
                CCDS_SEQ_TABLE, self._source_version
            )

            logger.info(
                "ccds_seq_load_complete",
                extra={"rows_loaded": count},
            )

            return CcdsSeqLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "ccds_seq_load_failed",
                extra={"error": str(exc)},
            )
            return CcdsSeqLoadResult(success=False, error=str(exc))
