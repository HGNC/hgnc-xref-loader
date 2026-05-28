"""Ensembl sequence FASTA parser for combined cDNA + ncRNA data.

Parses Ensembl FASTA files (cDNA and ncRNA) extracting gene/transcript
IDs from deflines and concatenating sequence lines.

Staging table columns:
    eseq_source, eseq_defline, eseq_ensembl_gene_id,
    eseq_ensembl_transcript_id, eseq_seq, eseq_length
"""

from __future__ import annotations

import gzip
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

GENE_RE = re.compile(r"(ENSG\d+)")
TRANSCRIPT_RE = re.compile(r"(ENST\d+)")


@dataclass(frozen=True)
class EnsemblSeqRecord:
    """A single ensembl_seq staging row.

    Attributes:
        eseq_source: Source type (cdna or ncrna).
        eseq_defline: Full FASTA defline (without >).
        eseq_ensembl_gene_id: Ensembl gene stable ID.
        eseq_ensembl_transcript_id: Ensembl transcript stable ID.
        eseq_seq: Nucleotide sequence.
        eseq_length: Sequence length.
    """

    eseq_source: str
    eseq_defline: str
    eseq_ensembl_gene_id: str
    eseq_ensembl_transcript_id: str
    eseq_seq: str
    eseq_length: int

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "eseq_source": self.eseq_source,
            "eseq_defline": self.eseq_defline,
            "eseq_ensembl_gene_id": self.eseq_ensembl_gene_id,
            "eseq_ensembl_transcript_id": self.eseq_ensembl_transcript_id,
            "eseq_seq": self.eseq_seq,
            "eseq_length": self.eseq_length,
        }


class EnsemblSeqParser:
    """Parse Ensembl FASTA (cDNA + ncRNA) into EnsemblSeqRecord rows."""

    def parse_cdna(self, data: bytes) -> list[EnsemblSeqRecord]:
        """Parse gzip-compressed cDNA FASTA data.

        Args:
            data: Raw gzip bytes from Ensembl FTP.

        Returns:
            List of ``EnsemblSeqRecord`` instances sourced as 'cdna'.
        """
        return self._parse_fasta(data, "cdna")

    def parse_ncrna(self, data: bytes) -> list[EnsemblSeqRecord]:
        """Parse gzip-compressed ncRNA FASTA data.

        Args:
            data: Raw gzip bytes from Ensembl FTP.

        Returns:
            List of ``EnsemblSeqRecord`` instances sourced as 'ncrna'.
        """
        return self._parse_fasta(data, "ncrna")

    def _parse_fasta(self, data: bytes, source: str) -> list[EnsemblSeqRecord]:
        """Parse gzip-compressed FASTA data with a source tag."""
        decompressed = gzip.decompress(data).decode("utf-8")
        records: list[EnsemblSeqRecord] = []
        defline: str = ""
        seq_parts: list[str] = []

        for line in decompressed.splitlines():
            if line.startswith(">"):
                if defline and seq_parts:
                    records.append(self._make_record(defline, seq_parts, source))
                defline = line[1:].strip()
                seq_parts = []
            else:
                seq_parts.append(line.strip())

        if defline and seq_parts:
            records.append(self._make_record(defline, seq_parts, source))

        logger.info(
            "ensembl_seq_parsed",
            extra={"source": source, "record_count": len(records)},
        )
        return records

    @staticmethod
    def _make_record(
        defline: str, seq_parts: list[str], source: str
    ) -> EnsemblSeqRecord:
        """Create a record from defline and sequence parts."""
        gene_match = GENE_RE.search(defline)
        tx_match = TRANSCRIPT_RE.search(defline)
        seq = "".join(seq_parts)

        return EnsemblSeqRecord(
            eseq_source=source,
            eseq_defline=defline,
            eseq_ensembl_gene_id=gene_match.group(1) if gene_match else "",
            eseq_ensembl_transcript_id=tx_match.group(1) if tx_match else "",
            eseq_seq=seq,
            eseq_length=len(seq),
        )
