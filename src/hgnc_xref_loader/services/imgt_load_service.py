"""IMGT load service.

Orchestrates the IMGT/GENE-DB load pipeline: HTTP form POST to IMGT,
parse HTML response, stage, and promote.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

IMGT_URL = "https://www.imgt.org/genedb/GENElect"
IMGT_TABLE = "imgt"
IMGT_STAGING = "imgt_update"

IMGT_FORM_DATA = {
    "query": "4.5 ",
    "species": "Homo sapiens",
    "receptor": "TR",
    "geneType": "all",
    "dataSet": "gene",
}

IMGT_COLUMNS = [
    "im_species", "im_gene_id", "im_gene_function", "im_gene_name",
    "im_alleles", "im_chrom", "im_ref_acc", "im_hgnc_app_sym",
    "im_hgnc_id", "im_eg_id", "im_vega", "im_geneatlas",
    "im_genecards", "im_uniprot",
]


@dataclass
class ImgtLoadResult:
    """Outcome of an IMGT load run."""

    success: bool = False
    skipped: bool = False
    rows_loaded: int = 0
    error: str = ""


class ImgtLoadService:
    """Orchestrate the IMGT load pipeline.

    Args:
        http_client: HTTP client supporting form POST.
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

    def run(self) -> ImgtLoadResult:
        """Execute the fetch->parse->stage->promote pipeline.

        Returns:
            A ``ImgtLoadResult`` describing the outcome.
        """
        try:
            if self._version_tracker.should_skip(
                IMGT_TABLE, self._source_version
            ):
                return ImgtLoadResult(success=True, skipped=True)

            data = self._http_client.fetch(
                url=IMGT_URL, method="POST", data=IMGT_FORM_DATA
            )
            records = self._parse_imgt(data)

            self._staging_repo.prepare_staging_table(IMGT_TABLE)

            count = self._staging_repo.bulk_copy_into_staging(
                IMGT_STAGING, records
            )

            self._staging_repo.promote_staging_to_production(
                IMGT_STAGING, IMGT_TABLE
            )

            self._version_tracker.record_version(
                IMGT_TABLE, self._source_version
            )

            logger.info(
                "imgt_load_complete",
                extra={"rows_loaded": count},
            )

            return ImgtLoadResult(success=True, rows_loaded=count)
        except Exception as exc:
            logger.error(
                "imgt_load_failed",
                extra={"error": str(exc)},
            )
            return ImgtLoadResult(success=False, error=str(exc))

    @staticmethod
    def _parse_imgt(data: bytes) -> list[dict[str, str]]:
        """Parse IMGT TSV response data.

        Args:
            data: Raw TSV bytes from IMGT.

        Returns:
            List of dicts with IMGT staging column names.
        """
        text = data.decode("utf-8")
        records: list[dict[str, str]] = []

        for line in text.splitlines():
            cols = line.split("\t")
            if len(cols) < 14:
                continue

            record: dict[str, str] = {}
            for i, col_name in enumerate(IMGT_COLUMNS):
                val = cols[i].strip() if i < len(cols) else ""
                record[col_name] = "" if val == "-" else val

            records.append(record)

        logger.info(
            "imgt_parsed",
            extra={"record_count": len(records)},
        )
        return records
