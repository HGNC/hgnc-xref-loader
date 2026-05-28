"""CCDS load service orchestrating FTP fetch, parsing, staging, and promotion.

Coordinates the full CCDS loader lifecycle:
1. Fetch CCDS.current.txt from NCBI FTP
2. Parse TSV into CcdsRecord instances
3. Load into ccds_update staging table via COPY
4. Validate row counts
5. Promote staging to production via ALTER TABLE RENAME

FTP/parsing errors propagate up. Staging promotion is skipped for empty
data sets. The service depends on injected FTP client and staging repo.
"""

from __future__ import annotations

import logging

from hgnc_xref_loader.fetch.ftp_client import CcdsFtpClient
from hgnc_xref_loader.loaders.ccds_parser import CcdsTsvParser
from hgnc_xref_loader.repositories.xref_staging_repository import XrefStagingRepository

logger = logging.getLogger(__name__)

SOURCE_TABLE = "ccds"


class CcdsLoadService:
    """Orchestrate the CCDS fetch-parse-stage-promote lifecycle.

    Args:
        ftp_client: Client for downloading CCDS data from NCBI FTP.
        staging_repo: Repository for staging table lifecycle operations.
    """

    def __init__(
        self,
        ftp_client: CcdsFtpClient,
        staging_repo: XrefStagingRepository,
    ) -> None:
        self._ftp_client = ftp_client
        self._staging_repo = staging_repo

    def run(self) -> int:
        """Execute the full CCDS load lifecycle.

        Returns:
            Number of records loaded into staging.

        Raises:
            FtpFetchError: If FTP download fails.
            RowCountMismatchError: If staging row count validation fails.
            StagingPromotionError: If promotion DDL fails.
        """
        raw_bytes = self._ftp_client.fetch()

        parser = CcdsTsvParser()
        records = parser.parse_bytes(raw_bytes)

        if not records:
            logger.info(
                "ccds_load_empty",
                extra={"event": "ccds_load_empty"},
            )
            return 0

        staging_dicts = [r.to_staging_dict() for r in records]
        staging_table = self._staging_repo.prepare_staging_table(SOURCE_TABLE)

        row_count = self._staging_repo.bulk_copy_into_staging(staging_table, staging_dicts)

        self._staging_repo.validate_staging_row_count(staging_table, row_count)
        self._staging_repo.promote_staging_to_production(staging_table, SOURCE_TABLE)

        logger.info(
            "ccds_load_complete",
            extra={
                "event": "ccds_load_complete",
                "records": row_count,
                "staging_table": staging_table,
            },
        )

        return row_count
