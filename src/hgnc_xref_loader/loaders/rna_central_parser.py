"""RNA Central TSV parser for RNAcentral id_mapping.tsv.gz data.

Parses the gzip-compressed RNAcentral id_mapping file, filtering rows
where the database column equals 'HGNC' and stripping the 'HGNC:' prefix
from the identifier column.

Staging table columns:
    rna_central_acc, hgnc_id, symbol, biotype, id
"""

from __future__ import annotations

import csv
import gzip
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1


@dataclass(frozen=True)
class RnaCentralRecord:
    """A single rna_central staging row.

    Attributes:
        rna_central_acc: RNAcentral accession.
        hgnc_id: HGNC numeric ID (stripped of HGNC: prefix).
        symbol: Gene symbol.
        biotype: Biotype annotation.
        id: Sequential row ID.
    """

    rna_central_acc: str
    hgnc_id: str
    symbol: str
    biotype: str
    id: int

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "rna_central_acc": self.rna_central_acc,
            "hgnc_id": self.hgnc_id,
            "symbol": self.symbol,
            "biotype": self.biotype,
            "id": self.id,
        }


class RnaCentralParser:
    """Parse RNAcentral id_mapping.tsv.gz into RnaCentralRecord staging rows.

    Filters for rows where the database name column equals 'HGNC' and
    strips the 'HGNC:' prefix from the identifier.
    """

    def parse(self, data: bytes) -> list[RnaCentralRecord]:
        """Parse gzip-compressed RNAcentral id_mapping data.

        Args:
            data: Raw gzip bytes from RNAcentral FTP.

        Returns:
            List of ``RnaCentralRecord`` instances for HGNC entries.
        """
        decompressed = gzip.decompress(data).decode("utf-8")
        lines = decompressed.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[RnaCentralRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")
        seq_id = 0

        for cols in reader:
            if len(cols) < 6:
                continue

            if cols[1].strip() != "HGNC":
                continue

            hgnc_id = cols[2].strip().replace("HGNC:", "")
            seq_id += 1

            records.append(
                RnaCentralRecord(
                    rna_central_acc=cols[0].strip(),
                    hgnc_id=hgnc_id,
                    symbol=self._clean(cols[5]),
                    biotype=self._clean(cols[4]),
                    id=seq_id,
                )
            )

        logger.info(
            "rna_central_parsed",
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
