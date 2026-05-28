"""Gene2Accession TSV parser for NCBI gene2accession.gz data.

Parses the gzip-compressed NCBI gene2accession file, filtering to accepted
tax IDs (9606 human, 10090 mouse, 10116 rat).

Staging table columns:
    g2a_tax_id, g2a_eg_id, g2a_status, g2a_rna_nt_acc_ver, g2a_rna_nt_gi,
    g2a_prot_acc_ver, g2a_prot_gi, g2a_gen_nt_acc_ver, g2a_gen_nt_gi,
    g2a_start_pos_gen_acc, g2a_end_pos_gen_acc, g2a_orientation, g2a_assembly,
    g2a_mat_pept_acc, g2a_mat_pept_gi, g2a_symbol
"""

from __future__ import annotations

import csv
import gzip
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1
ACCEPTED_TAX_IDS = {"9606", "10090", "10116"}


@dataclass(frozen=True)
class Gene2AccessionRecord:
    """A single gene2accession staging row.

    Attributes:
        g2a_tax_id: NCBI taxonomy ID.
        g2a_eg_id: Entrez Gene ID.
        g2a_status: Gene status.
        g2a_rna_nt_acc_ver: RNA nucleotide accession.version.
        g2a_rna_nt_gi: RNA nucleotide GI.
        g2a_prot_acc_ver: Protein accession.version.
        g2a_prot_gi: Protein GI.
        g2a_gen_nt_acc_ver: Genomic nucleotide accession.version.
        g2a_gen_nt_gi: Genomic nucleotide GI.
        g2a_start_pos_gen_acc: Start position on genomic accession.
        g2a_end_pos_gen_acc: End position on genomic accession.
        g2a_orientation: Orientation.
        g2a_assembly: Assembly.
        g2a_mat_pept_acc: Mature peptide accession.
        g2a_mat_pept_gi: Mature peptide GI.
        g2a_symbol: Gene symbol.
    """

    g2a_tax_id: str
    g2a_eg_id: str
    g2a_status: str
    g2a_rna_nt_acc_ver: str
    g2a_rna_nt_gi: str
    g2a_prot_acc_ver: str
    g2a_prot_gi: str
    g2a_gen_nt_acc_ver: str
    g2a_gen_nt_gi: str
    g2a_start_pos_gen_acc: str
    g2a_end_pos_gen_acc: str
    g2a_orientation: str
    g2a_assembly: str
    g2a_mat_pept_acc: str
    g2a_mat_pept_gi: str
    g2a_symbol: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "g2a_tax_id": self.g2a_tax_id,
            "g2a_eg_id": self.g2a_eg_id,
            "g2a_status": self.g2a_status,
            "g2a_rna_nt_acc_ver": self.g2a_rna_nt_acc_ver,
            "g2a_rna_nt_gi": self.g2a_rna_nt_gi,
            "g2a_prot_acc_ver": self.g2a_prot_acc_ver,
            "g2a_prot_gi": self.g2a_prot_gi,
            "g2a_gen_nt_acc_ver": self.g2a_gen_nt_acc_ver,
            "g2a_gen_nt_gi": self.g2a_gen_nt_gi,
            "g2a_start_pos_gen_acc": self.g2a_start_pos_gen_acc,
            "g2a_end_pos_gen_acc": self.g2a_end_pos_gen_acc,
            "g2a_orientation": self.g2a_orientation,
            "g2a_assembly": self.g2a_assembly,
            "g2a_mat_pept_acc": self.g2a_mat_pept_acc,
            "g2a_mat_pept_gi": self.g2a_mat_pept_gi,
            "g2a_symbol": self.g2a_symbol,
        }


class Gene2AccessionParser:
    """Parse NCBI gene2accession.gz into Gene2AccessionRecord staging rows.

    Filters by accepted tax IDs (human, mouse, rat).
    """

    def parse(self, data: bytes) -> list[Gene2AccessionRecord]:
        """Parse gzip-compressed gene2accession data.

        Args:
            data: Raw gzip bytes from NCBI.

        Returns:
            List of ``Gene2AccessionRecord`` instances for accepted tax IDs.
        """
        decompressed = gzip.decompress(data).decode("utf-8")
        lines = decompressed.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[Gene2AccessionRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")

        for cols in reader:
            if len(cols) < 16:
                continue

            tax_id = cols[0].strip()
            if tax_id not in ACCEPTED_TAX_IDS:
                continue

            records.append(
                Gene2AccessionRecord(
                    g2a_tax_id=tax_id,
                    g2a_eg_id=self._clean(cols[1]),
                    g2a_status=self._clean(cols[2]),
                    g2a_rna_nt_acc_ver=self._clean(cols[3]),
                    g2a_rna_nt_gi=self._clean(cols[4]),
                    g2a_prot_acc_ver=self._clean(cols[5]),
                    g2a_prot_gi=self._clean(cols[6]),
                    g2a_gen_nt_acc_ver=self._clean(cols[7]),
                    g2a_gen_nt_gi=self._clean(cols[8]),
                    g2a_start_pos_gen_acc=self._clean(cols[9]),
                    g2a_end_pos_gen_acc=self._clean(cols[10]),
                    g2a_orientation=self._clean(cols[11]),
                    g2a_assembly=self._clean(cols[12]),
                    g2a_mat_pept_acc=self._clean(cols[13]),
                    g2a_mat_pept_gi=self._clean(cols[14]),
                    g2a_symbol=self._clean(cols[15]),
                )
            )

        logger.info(
            "gene2accession_parsed",
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
