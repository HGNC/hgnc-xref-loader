"""NCBI to NameList parser for NCBI to_name FTP data.

Parses the plain-text NCBI to_name file (tab-separated, no header).

Staging table columns:
    ntn_eg_id, ntn_sym
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Ncbi2NamelistRecord:
    """A single ncbi2namelist staging row.

    Attributes:
        ntn_eg_id: Entrez Gene ID.
        ntn_sym: Gene symbol.
    """

    ntn_eg_id: str
    ntn_sym: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "ntn_eg_id": self.ntn_eg_id,
            "ntn_sym": self.ntn_sym,
        }


class Ncbi2NamelistParser:
    """Parse NCBI to_name into Ncbi2NamelistRecord staging rows."""

    def parse(self, data: bytes) -> list[Ncbi2NamelistRecord]:
        """Parse plain-text NCBI to_name data.

        Args:
            data: Raw bytes from NCBI FTP.

        Returns:
            List of ``Ncbi2NamelistRecord`` instances.
        """
        text = data.decode("utf-8")
        records: list[Ncbi2NamelistRecord] = []
        reader = csv.reader(io.StringIO(text), delimiter="\t")

        for cols in reader:
            if len(cols) < 2:
                continue

            eg_id = cols[0].strip()
            sym = cols[1].strip()

            if not eg_id or not sym:
                continue

            records.append(
                Ncbi2NamelistRecord(
                    ntn_eg_id=eg_id,
                    ntn_sym=sym,
                )
            )

        logger.info(
            "ncbi2namelist_parsed",
            extra={"record_count": len(records)},
        )
        return records
