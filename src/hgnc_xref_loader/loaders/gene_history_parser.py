"""Gene history TSV parser for NCBI gene_history.gz data.

Parses the gzip-compressed NCBI gene_history file, filtering to accepted
tax IDs (9606 human, 10090 mouse, 10116 rat).

Staging table columns:
    gh_tax_id, gh_eg_id, gh_discontinued_eg_id, gh_discontinued_sym,
    gh_discontinued_date
"""

from __future__ import annotations

import csv
import gzip
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1
ACCEPTED_TAX_IDS = {"9606", "10090", "10116"}

STAGING_COLUMNS = [
    "gh_tax_id",
    "gh_eg_id",
    "gh_discontinued_eg_id",
    "gh_discontinued_sym",
    "gh_discontinued_date",
]


@dataclass(frozen=True)
class GeneHistoryRecord:
    """A single gene_history staging row.

    Attributes:
        gh_tax_id: NCBI taxonomy ID.
        gh_eg_id: Current Entrez Gene ID.
        gh_discontinued_eg_id: Discontinued Entrez Gene ID.
        gh_discontinued_sym: Discontinued gene symbol.
        gh_discontinued_date: Date the gene was discontinued.
    """

    gh_tax_id: str
    gh_eg_id: str
    gh_discontinued_eg_id: str
    gh_discontinued_sym: str
    gh_discontinued_date: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "gh_tax_id": self.gh_tax_id,
            "gh_eg_id": self.gh_eg_id,
            "gh_discontinued_eg_id": self.gh_discontinued_eg_id,
            "gh_discontinued_sym": self.gh_discontinued_sym,
            "gh_discontinued_date": self.gh_discontinued_date,
        }


class GeneHistoryParser:
    """Parse NCBI gene_history.gz into GeneHistoryRecord staging rows.

    Filters by accepted tax IDs (human, mouse, rat).
    """

    def parse(self, data: bytes) -> list[GeneHistoryRecord]:
        """Parse gzip-compressed gene_history data.

        Args:
            data: Raw gzip bytes from NCBI.

        Returns:
            List of ``GeneHistoryRecord`` instances for accepted tax IDs.
        """
        decompressed = gzip.decompress(data).decode("utf-8")
        lines = decompressed.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[GeneHistoryRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")

        for cols in reader:
            if len(cols) < 5:
                continue

            tax_id = cols[0].strip()
            if tax_id not in ACCEPTED_TAX_IDS:
                continue

            records.append(
                GeneHistoryRecord(
                    gh_tax_id=tax_id,
                    gh_eg_id=self._clean(cols[1]),
                    gh_discontinued_eg_id=self._clean(cols[2]),
                    gh_discontinued_sym=self._clean(cols[3]),
                    gh_discontinued_date=self._clean(cols[4]),
                )
            )

        logger.info(
            "gene_history_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _clean(val: str) -> str:
        """Clean a TSV field value.

        Args:
            val: Raw field value.

        Returns:
            Empty string for ``-`` or blank values; otherwise stripped.
        """
        stripped = val.strip()
        return "" if stripped == "-" else stripped
