"""MANE TSV parser for NCBI MANE summary data.

Parses the gzip-compressed NCBI MANE.GRCh38.v*.summary.txt.gz file.
Strips GeneID: and HGNC: prefixes and adds a sequential id column.

Staging table columns:
    ncbi_gene_id, ensembl_gene, hgnc_id, symbol, gene_name,
    refseq_nuc_acc, refseq_prot_acc, ensembl_nuc_acc, ensembl_prot_acc,
    mane_status, grch38_chr, grch38_chr_start, grch38_chr_end,
    grch38_chr_strand, id
"""

from __future__ import annotations

import csv
import gzip
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1
GENE_ID_PREFIX = re.compile(r"^GeneID:")
HGNC_PREFIX = re.compile(r"^HGNC:")


@dataclass(frozen=True)
class ManeRecord:
    """A single MANE staging row.

    Attributes:
        ncbi_gene_id: NCBI Gene ID (stripped of GeneID: prefix).
        ensembl_gene: Ensembl gene ID.
        hgnc_id: HGNC numeric ID (stripped of HGNC: prefix).
        symbol: Gene symbol.
        gene_name: Gene name.
        refseq_nuc_acc: RefSeq nucleotide accession.
        refseq_prot_acc: RefSeq protein accession.
        ensembl_nuc_acc: Ensembl nucleotide accession.
        ensembl_prot_acc: Ensembl protein accession.
        mane_status: MANE status (MANE Select / MANE Plus Clinical).
        grch38_chr: GRCh38 chromosome.
        grch38_chr_start: GRCh38 start position.
        grch38_chr_end: GRCh38 end position.
        grch38_chr_strand: GRCh38 strand.
        id: Sequential row ID.
    """

    ncbi_gene_id: int
    ensembl_gene: str
    hgnc_id: int
    symbol: str
    gene_name: str
    refseq_nuc_acc: str
    refseq_prot_acc: str
    ensembl_nuc_acc: str
    ensembl_prot_acc: str
    mane_status: str
    grch38_chr: str
    grch38_chr_start: int
    grch38_chr_end: int
    grch38_chr_strand: str
    id: int

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "ncbi_gene_id": self.ncbi_gene_id,
            "ensembl_gene": self.ensembl_gene,
            "hgnc_id": self.hgnc_id,
            "symbol": self.symbol,
            "gene_name": self.gene_name,
            "refseq_nuc_acc": self.refseq_nuc_acc,
            "refseq_prot_acc": self.refseq_prot_acc,
            "ensembl_nuc_acc": self.ensembl_nuc_acc,
            "ensembl_prot_acc": self.ensembl_prot_acc,
            "mane_status": self.mane_status,
            "grch38_chr": self.grch38_chr,
            "grch38_chr_start": self.grch38_chr_start,
            "grch38_chr_end": self.grch38_chr_end,
            "grch38_chr_strand": self.grch38_chr_strand,
            "id": self.id,
        }


class ManeParser:
    """Parse NCBI MANE summary TSV into ManeRecord staging rows."""

    def parse(self, data: bytes) -> list[ManeRecord]:
        """Parse gzip-compressed MANE summary data.

        Args:
            data: Raw gzip bytes from NCBI.

        Returns:
            List of ``ManeRecord`` instances.
        """
        decompressed = gzip.decompress(data).decode("utf-8")
        lines = decompressed.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[ManeRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")
        seq_id = 0

        for cols in reader:
            if len(cols) < 14:
                continue

            seq_id += 1

            ncbi_gene_id = self._strip_int(cols[0], "GeneID:")
            ensembl_gene = self._clean(cols[1])
            hgnc_id = self._strip_int(cols[2], "HGNC:")

            records.append(
                ManeRecord(
                    ncbi_gene_id=ncbi_gene_id,
                    ensembl_gene=ensembl_gene.split(".")[0] if ensembl_gene else "",
                    hgnc_id=hgnc_id,
                    symbol=self._clean(cols[3]),
                    gene_name=self._clean(cols[4]),
                    refseq_nuc_acc=self._clean(cols[5]),
                    refseq_prot_acc=self._clean(cols[6]),
                    ensembl_nuc_acc=self._clean(cols[7]),
                    ensembl_prot_acc=self._clean(cols[8]),
                    mane_status=self._clean(cols[9]),
                    grch38_chr=self._clean(cols[10]),
                    grch38_chr_start=self._safe_int(self._clean(cols[11])),
                    grch38_chr_end=self._safe_int(self._clean(cols[12])),
                    grch38_chr_strand=self._clean(cols[13]),
                    id=seq_id,
                )
            )

        logger.info(
            "mane_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _clean(val: str) -> str:
        """Clean a TSV field value."""
        stripped = val.strip()
        return "" if stripped == "-" else stripped

    @staticmethod
    def _strip_int(val: str, prefix: str) -> int:
        """Strip a prefix and parse as int."""
        stripped = val.strip()
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
        try:
            return int(stripped)
        except ValueError:
            return 0

    @staticmethod
    def _safe_int(val: str) -> int:
        """Parse an integer, returning 0 on failure."""
        try:
            return int(val)
        except ValueError:
            return 0
