"""CCDS TSV parser for CCDS.current.txt.

Parses the NCBI CCDS tab-separated file into validated CcdsRecord instances
suitable for bulk loading into the ccds_update staging table. Follows the
column layout from the Perl HGNC::DB::PostgreSQL::Genew4::Load::Table::CCDS
module: chromosome, accession, version, symbol, ncbi_gene_id, ccds_id,
status, strand, from, to, locations, match_type.

Empty values and ``-`` are normalised to empty strings to match the Perl
loader's ``ne '-'`` convention.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import TextIO

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = 12


class CcdsParseError(Exception):
    """Raised when CCDS TSV parsing encounters an unrecoverable error."""


@dataclass
class CcdsRecord:
    """A single parsed CCDS row matching the ccds_update staging schema.

    Attributes:
        chromosome: Chromosome name (e.g. ``chr1``).
        accession: NCBI accession (e.g. ``NC_000001.11``).
        symbol: Gene symbol.
        ncbi_gene_id: NCBI Entrez Gene ID.
        ccds_id: CCDS identifier (e.g. ``CCDS1.1``).
        status: CCDS status (e.g. ``Public``, ``Withdrawn``).
        strand: Genomic strand (``+`` or ``-``).
        start: Start coordinate.
        end: End coordinate.
        locations: Location string (typically ``;``).
        match_type: Match type (typically ``NotAvailable``).
    """

    chromosome: str
    accession: str
    symbol: str
    ncbi_gene_id: str
    ccds_id: str
    status: str
    strand: str
    start: str
    end: str
    locations: str
    match_type: str

    def to_staging_dict(self) -> dict[str, str]:
        """Convert to a dict keyed by staging table column names.

        Dash values and empty strings are converted to empty strings
        matching the Perl loader convention.

        Returns:
            Dictionary with ccds_* column names as keys.
        """
        return {
            "ccds_chrom": _normalise(self.chromosome),
            "ccds_acc": _normalise(self.accession),
            "ccds_sym": _normalise(self.symbol),
            "ccds_eg_id": _normalise(self.ncbi_gene_id),
            "ccds_id": _normalise(self.ccds_id),
            "ccds_status": _normalise(self.status),
            "ccds_strand": _normalise(self.strand),
            "ccds_from": _normalise(self.start),
            "ccds_to": _normalise(self.end),
            "ccds_locations": _normalise(self.locations),
            "ccds_match_type": _normalise(self.match_type),
        }


def _normalise(value: str) -> str:
    if value == "-" or not value.strip():
        return ""
    return value.strip()


class CcdsTsvParser:
    """Streaming TSV parser for CCDS.current.txt.

    Skips the first header line, splits on tab, trims whitespace, and
    yields CcdsRecord instances. Rows with fewer than 12 columns or
    missing CCDS IDs are silently skipped.

    Args:
        skip_header: Number of header lines to skip. Defaults to 1.
    """

    def __init__(self, skip_header: int = 1) -> None:
        self._skip_header = skip_header

    def parse(self, stream: TextIO) -> list[CcdsRecord]:
        """Parse a text stream of CCDS TSV data into records.

        Args:
            stream: Text stream containing CCDS TSV data.

        Returns:
            List of validated CcdsRecord instances.
        """
        records: list[CcdsRecord] = []
        for line_number, line in enumerate(stream, start=1):
            if line_number <= self._skip_header:
                continue
            record = self._parse_line(line)
            if record is not None:
                records.append(record)
        return records

    def parse_bytes(self, data: bytes) -> list[CcdsRecord]:
        """Parse raw bytes of CCDS TSV data into records.

        Args:
            data: Raw bytes of the CCDS file.

        Returns:
            List of validated CcdsRecord instances.
        """
        return self.parse(io.StringIO(data.decode("utf-8")))

    def _parse_line(self, line: str) -> CcdsRecord | None:
        stripped = line.strip()
        if not stripped:
            return None

        cols = stripped.split("\t")
        if len(cols) < EXPECTED_COLUMNS:
            logger.warning(
                "ccds_parse_skip_short_row",
                extra={"columns": len(cols), "expected": EXPECTED_COLUMNS},
            )
            return None

        fields = [c.strip() for c in cols[:EXPECTED_COLUMNS]]

        ccds_id = fields[5]
        if not ccds_id or ccds_id == "-":
            return None

        return CcdsRecord(
            chromosome=fields[0],
            accession=fields[1],
            symbol=fields[3],
            ncbi_gene_id=fields[4],
            ccds_id=ccds_id,
            status=fields[6],
            strand=fields[7],
            start=fields[8],
            end=fields[9],
            locations=fields[10],
            match_type=fields[11],
        )
