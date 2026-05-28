"""MGI TSV parser for MGI Alliance homology report.

Parses TSV data from the MGI HGNC_AllianceHomology.rpt file.

Staging table columns:
    mgi_id, symbol, name, type, ncbi_gene_id, ncbi_gene_chr,
    ncbi_gene_start, ncbi_gene_end, ncbi_gene_strand, ensembl_id,
    ensembl_chr, ensembl_start, ensembl_end, ensembl_strand
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1


@dataclass(frozen=True)
class MgiRecord:
    """A single MGI staging row.

    Attributes:
        mgi_id: MGI identifier.
        symbol: Gene symbol.
        name: Gene name.
        type: Feature type.
        ncbi_gene_id: NCBI Gene ID.
        ncbi_gene_chr: NCBI chromosome.
        ncbi_gene_start: NCBI start position.
        ncbi_gene_end: NCBI end position.
        ncbi_gene_strand: NCBI strand.
        ensembl_id: Ensembl gene ID.
        ensembl_chr: Ensembl chromosome.
        ensembl_start: Ensembl start position.
        ensembl_end: Ensembl end position.
        ensembl_strand: Ensembl strand.
    """

    mgi_id: str
    symbol: str
    name: str
    type: str
    ncbi_gene_id: str
    ncbi_gene_chr: str
    ncbi_gene_start: str
    ncbi_gene_end: str
    ncbi_gene_strand: str
    ensembl_id: str
    ensembl_chr: str
    ensembl_start: str
    ensembl_end: str
    ensembl_strand: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "mgi_id": self.mgi_id,
            "symbol": self.symbol,
            "name": self.name,
            "type": self.type,
            "ncbi_gene_id": self.ncbi_gene_id,
            "ncbi_gene_chr": self.ncbi_gene_chr,
            "ncbi_gene_start": self.ncbi_gene_start,
            "ncbi_gene_end": self.ncbi_gene_end,
            "ncbi_gene_strand": self.ncbi_gene_strand,
            "ensembl_id": self.ensembl_id,
            "ensembl_chr": self.ensembl_chr,
            "ensembl_start": self.ensembl_start,
            "ensembl_end": self.ensembl_end,
            "ensembl_strand": self.ensembl_strand,
        }


class MgiParser:
    """Parse MGI homology TSV into MgiRecord staging rows."""

    def parse(self, data: bytes) -> list[MgiRecord]:
        """Parse MGI homology report TSV data.

        Args:
            data: Raw TSV bytes from MGI.

        Returns:
            List of ``MgiRecord`` instances.
        """
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[MgiRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")

        for cols in reader:
            if len(cols) < 14:
                continue

            records.append(
                MgiRecord(
                    mgi_id=self._clean(cols[0]),
                    symbol=self._clean(cols[1]),
                    name=self._clean(cols[2]),
                    type=self._clean(cols[3]),
                    ncbi_gene_id=self._clean(cols[4]),
                    ncbi_gene_chr=self._clean(cols[5]),
                    ncbi_gene_start=self._clean(cols[6]),
                    ncbi_gene_end=self._clean(cols[7]),
                    ncbi_gene_strand=self._clean(cols[8]),
                    ensembl_id=self._clean(cols[9]),
                    ensembl_chr=self._clean(cols[10]),
                    ensembl_start=self._clean(cols[11]),
                    ensembl_end=self._clean(cols[12]),
                    ensembl_strand=self._clean(cols[13]),
                )
            )

        logger.info(
            "mgi_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _clean(val: str) -> str:
        """Clean a TSV field value."""
        stripped = val.strip()
        return "" if stripped == "-" else stripped
