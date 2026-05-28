"""AGR TSV parser for Alliance genome gene descriptions.

Parses TSV data from the Alliance of Genome Resources, stripping
HGNC: prefix from the HGNC ID column.

Staging table columns:
    hgnc_id, symbol, description
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1


@dataclass(frozen=True)
class AgrRecord:
    """A single AGR staging row.

    Attributes:
        hgnc_id: HGNC numeric ID (stripped of HGNC: prefix).
        symbol: Gene symbol.
        description: Gene description (empty if 'No description available').
    """

    hgnc_id: int
    symbol: str
    description: str

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "hgnc_id": self.hgnc_id,
            "symbol": self.symbol,
            "description": self.description,
        }


class AgrParser:
    """Parse Alliance genome TSV into AgrRecord staging rows."""

    def parse(self, data: bytes) -> list[AgrRecord]:
        """Parse AGR gene description TSV data.

        Args:
            data: Raw TSV bytes from Alliance.

        Returns:
            List of ``AgrRecord`` instances with valid HGNC IDs.
        """
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[AgrRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")

        for cols in reader:
            if len(cols) < 3:
                continue

            hgnc_str = cols[0].strip().replace("HGNC:", "")
            try:
                hgnc_id = int(hgnc_str)
            except ValueError:
                continue

            desc = cols[2].strip()
            if desc == "No description available":
                desc = ""

            records.append(
                AgrRecord(
                    hgnc_id=hgnc_id,
                    symbol=cols[1].strip(),
                    description=desc,
                )
            )

        logger.info(
            "agr_parsed",
            extra={"record_count": len(records)},
        )
        return records
