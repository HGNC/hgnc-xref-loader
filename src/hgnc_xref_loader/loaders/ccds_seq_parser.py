"""CCDS Sequence FASTA parser for NCBI CCDS_nucleotide.current.fna.gz data.

Parses the gzip-compressed CCDS FASTA file, extracting CCDS ID, build,
chromosome from deflines and concatenating sequence lines.

Staging table columns:
    ccdseq_ccds_id, ccdseq_build, ccdseq_chrom, ccdseq_seq
"""

from __future__ import annotations

import gzip
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CcdsSeqRecord:
    """A single ccds_seq staging row.

    Attributes:
        ccdseq_ccds_id: CCDS identifier.
        ccdseq_build: Genome build (e.g. GRCh38).
        ccdseq_chrom: Chromosome name.
        ccdseq_seq: Nucleotide sequence.
    """

    ccdseq_ccds_id: str
    ccdseq_build: str
    ccdseq_chrom: str
    ccdseq_seq: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "ccdseq_ccds_id": self.ccdseq_ccds_id,
            "ccdseq_build": self.ccdseq_build,
            "ccdseq_chrom": self.ccdseq_chrom,
            "ccdseq_seq": self.ccdseq_seq,
        }


class CcdsSeqParser:
    """Parse NCBI CCDS_nucleotide.current.fna.gz into CcdsSeqRecord rows."""

    def parse(self, data: bytes) -> list[CcdsSeqRecord]:
        """Parse gzip-compressed CCDS FASTA data.

        Args:
            data: Raw gzip bytes from NCBI FTP.

        Returns:
            List of ``CcdsSeqRecord`` instances.
        """
        decompressed = gzip.decompress(data).decode("utf-8")
        records: list[CcdsSeqRecord] = []
        defline: str | None = None
        seq_parts: list[str] = []

        for line in decompressed.splitlines():
            if line.startswith(">"):
                if defline is not None and seq_parts:
                    records.append(self._make_record(defline, seq_parts))
                defline = line
                seq_parts = []
            else:
                seq_parts.append(line.strip())

        if defline is not None and seq_parts:
            records.append(self._make_record(defline, seq_parts))

        logger.info(
            "ccds_seq_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _make_record(defline: str, seq_parts: list[str]) -> CcdsSeqRecord:
        """Create a CcdsSeqRecord from a FASTA defline and sequence parts.

        Args:
            defline: FASTA header line starting with '>'.
            seq_parts: List of sequence line fragments.

        Returns:
            A ``CcdsSeqRecord`` with parsed defline fields.
        """
        header = defline.lstrip(">").strip()
        parts = header.split("|")
        ccds_id = parts[0].strip() if len(parts) > 0 else ""
        build = parts[1].strip() if len(parts) > 1 else ""
        chrom = parts[2].strip() if len(parts) > 2 else ""
        seq = "".join(seq_parts)

        return CcdsSeqRecord(
            ccdseq_ccds_id=ccds_id,
            ccdseq_build=build,
            ccdseq_chrom=chrom,
            ccdseq_seq=seq,
        )
