"""Ensembl sequence load service.

Orchestrates the Ensembl sequence load pipeline: download cDNA and ncRNA
FASTA from Ensembl FTP, parse, stage, and promote.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from hgnc_xref_loader.loaders.ensembl_seq_parser import EnsemblSeqParser

logger = logging.getLogger(__name__)

ENSEMBL_SEQ_TABLE = "ensembl_seq"
ENSEMBL_SEQ_STAGING = "ensembl_seq_update"


@dataclass
class EnsemblSeqLoadResult:
    """Outcome of an ensembl_seq load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class EnsemblSeqLoadService:
    """Orchestrate the Ensembl sequence load pipeline.

    Args:
        ftp_client: FTP client for Ensembl downloads.
        staging_repo: Postgres staging repository.
        version_tracker: Version tracking service.
        source_version: Current Ensembl version string.
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
        self._parser = EnsemblSeqParser()

    def run(self) -> EnsemblSeqLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``EnsemblSeqLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                ENSEMBL_SEQ_TABLE, self._source_version
            ):
                return EnsemblSeqLoadResult(success=True, skipped=True)

            cdna_data = self._ftp_client.fetch_cdna()
            ncrna_data = self._ftp_client.fetch_ncrna()

            cdna_records = self._parser.parse_cdna(cdna_data)
            ncrna_records = self._parser.parse_ncrna(ncrna_data)
            all_records = cdna_records + ncrna_records

            self._staging_repo.prepare_staging_table(ENSEMBL_SEQ_TABLE)

            staging_dicts = [r.to_staging_dict() for r in all_records]
            count = self._staging_repo.bulk_copy_into_staging(
                ENSEMBL_SEQ_STAGING, staging_dicts
            )

            self._staging_repo.promote_staging_to_production(
                ENSEMBL_SEQ_STAGING, ENSEMBL_SEQ_TABLE
            )

            self._version_tracker.record_version(
                ENSEMBL_SEQ_TABLE, self._source_version
            )

            logger.info(
                "ensembl_seq_load_complete",
                extra={"rows_loaded": count},
            )

            return EnsemblSeqLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "ensembl_seq_load_failed",
                extra={"error": str(exc)},
            )
            return EnsemblSeqLoadResult(success=False, error=str(exc))
