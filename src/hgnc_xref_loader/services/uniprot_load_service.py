"""UniProt load service orchestrating the 4-table pipeline.

Coordinates fetch, parse, staging, and promotion across the four
UniProt tables (main, has_hgnc, has_ncbi_gene, has_ec) with
version-aware skip logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from hgnc_xref_loader.fetch.uniprot_client import UniprotHttpClient
from hgnc_xref_loader.loaders.uniprot_parser import UniprotTsvParser
from hgnc_xref_loader.repositories.uniprot_staging_repository import (
    UniprotStagingRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class UniprotLoadResult:
    """Outcome of a UniProt load run.

    Attributes:
        success: Whether the load completed without error.
        skipped: Whether the load was skipped (version unchanged).
        version: The UniProt release version string.
        main_rows: Rows loaded into the main uniprot table.
        hgnc_rows: Rows loaded into the uniprot_has_hgnc junction table.
        ncbi_gene_rows: Rows loaded into the uniprot_has_ncbi_gene junction table.
        ec_rows: Rows loaded into the uniprot_has_ec junction table.
        error: Error message if the load failed.
    """

    success: bool = False
    skipped: bool = False
    version: str = ""
    main_rows: int = 0
    hgnc_rows: int = 0
    ncbi_gene_rows: int = 0
    ec_rows: int = 0
    error: str = ""


class UniprotLoadService:
    """Orchestrate the UniProt 4-table load pipeline.

    Fetches TSV from the UniProt REST API, parses into four sets of
    staging rows, bulk-loads into Postgres, and promotes staging to
    production.

    Args:
        http_client: UniProt HTTP fetch client.
        staging_repo: UniProt staging repository for DDL/COPY/promotion.
        version_tracker: Version tracking service for skip logic.
    """

    def __init__(
        self,
        http_client: Any,
        staging_repo: UniprotStagingRepository,
        version_tracker: Any,
    ) -> None:
        self._http_client = http_client
        self._staging_repo = staging_repo
        self._version_tracker = version_tracker
        self._parser = UniprotTsvParser()

    def run(self) -> UniprotLoadResult:
        """Execute the full fetch->parse->stage->promote pipeline.

        Returns:
            An ``UniprotLoadResult`` describing the outcome.
        """
        try:
            version = self._http_client.fetch_version()

            if self._version_tracker.is_current_version("uniprot", version):
                logger.info(
                    "uniprot_skip",
                    extra={"event": "uniprot_skip", "version": version},
                )
                return UniprotLoadResult(success=True, skipped=True, version=version)

            data, data_version = self._http_client.fetch()
            version = data_version or version

            batch = self._parser.parse(data)

            self._staging_repo.prepare_staging_tables()
            main_count = self._staging_repo.bulk_load_main(batch.main_rows)
            hgnc_count = self._staging_repo.bulk_load_hgnc(batch.hgnc_rows)
            ncbi_count = self._staging_repo.bulk_load_ncbi_gene(batch.ncbi_gene_rows)
            ec_count = self._staging_repo.bulk_load_ec(batch.ec_rows)

            self._staging_repo.promote_all()

            self._version_tracker.record_version("uniprot", version)

            logger.info(
                "uniprot_load_complete",
                extra={
                    "event": "uniprot_load_complete",
                    "version": version,
                    "main_rows": main_count,
                    "hgnc_rows": hgnc_count,
                    "ncbi_gene_rows": ncbi_count,
                    "ec_rows": ec_count,
                },
            )

            return UniprotLoadResult(
                success=True,
                version=version,
                main_rows=main_count,
                hgnc_rows=hgnc_count,
                ncbi_gene_rows=ncbi_count,
                ec_rows=ec_count,
            )
        except Exception as exc:
            logger.error(
                "uniprot_load_failed",
                extra={"event": "uniprot_load_failed", "error": str(exc)},
            )
            return UniprotLoadResult(success=False, error=str(exc))
