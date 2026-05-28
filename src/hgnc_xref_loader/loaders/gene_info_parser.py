"""Gene info TSV parser for NCBI gene_info.gz data.

Parses the gzip-compressed NCBI gene_info file, filtering to accepted
tax IDs (9606 human, 10090 mouse, 10116 rat) and extracting the HGNC
numeric ID from the dbXrefs column.

Staging table columns:
    gi_tax_id, gi_eg_id, gi_sym, gi_locustag, gi_synonyms,
    gi_dbxrefs, gi_chrom, gi_map_location, gi_description,
    gi_type_of_gene, gi_sym_from_nome_auth, gi_full_name_from_nome_auth,
    gi_nome_status, gi_other_designations, gi_modification_date, gi_hgnc_id
"""

from __future__ import annotations

import csv
import gzip
import io
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1
ACCEPTED_TAX_IDS = {"9606", "10090", "10116"}
HGNC_RE = re.compile(r"HGNC:(\d+)")
SKIP_EG_IDS = {"103277480"}

STAGING_COLUMNS = [
    "gi_tax_id",
    "gi_eg_id",
    "gi_sym",
    "gi_locustag",
    "gi_synonyms",
    "gi_dbxrefs",
    "gi_chrom",
    "gi_map_location",
    "gi_description",
    "gi_type_of_gene",
    "gi_sym_from_nome_auth",
    "gi_full_name_from_nome_auth",
    "gi_nome_status",
    "gi_other_designations",
    "gi_modification_date",
    "gi_hgnc_id",
]


@dataclass(frozen=True)
class GeneInfoRecord:
    """A single gene_info staging row.

    Attributes:
        gi_tax_id: NCBI taxonomy ID.
        gi_eg_id: Entrez Gene ID.
        gi_sym: Gene symbol.
        gi_locustag: Locus tag.
        gi_synonyms: Pipe-separated synonyms.
        gi_dbxrefs: Pipe-separated cross-references.
        gi_chrom: Chromosome.
        gi_map_location: Map location.
        gi_description: Gene description.
        gi_type_of_gene: Gene type.
        gi_sym_from_nome_auth: Symbol from nomenclature authority.
        gi_full_name_from_nome_auth: Full name from nomenclature authority.
        gi_nome_status: Nomenclature status.
        gi_other_designations: Other designations.
        gi_modification_date: Last modification date.
        gi_hgnc_id: HGNC numeric ID extracted from dbXrefs (0 if absent).
    """

    gi_tax_id: str
    gi_eg_id: str
    gi_sym: str
    gi_locustag: str
    gi_synonyms: str
    gi_dbxrefs: str
    gi_chrom: str
    gi_map_location: str
    gi_description: str
    gi_type_of_gene: str
    gi_sym_from_nome_auth: str
    gi_full_name_from_nome_auth: str
    gi_nome_status: str
    gi_other_designations: str
    gi_modification_date: str
    gi_hgnc_id: int

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "gi_tax_id": self.gi_tax_id,
            "gi_eg_id": self.gi_eg_id,
            "gi_sym": self.gi_sym,
            "gi_locustag": self.gi_locustag,
            "gi_synonyms": self.gi_synonyms,
            "gi_dbxrefs": self.gi_dbxrefs,
            "gi_chrom": self.gi_chrom,
            "gi_map_location": self.gi_map_location,
            "gi_description": self.gi_description,
            "gi_type_of_gene": self.gi_type_of_gene,
            "gi_sym_from_nome_auth": self.gi_sym_from_nome_auth,
            "gi_full_name_from_nome_auth": self.gi_full_name_from_nome_auth,
            "gi_nome_status": self.gi_nome_status,
            "gi_other_designations": self.gi_other_designations,
            "gi_modification_date": self.gi_modification_date,
            "gi_hgnc_id": self.gi_hgnc_id,
        }


class GeneInfoParser:
    """Parse NCBI gene_info.gz into GeneInfoRecord staging rows.

    Filters by accepted tax IDs and extracts HGNC numeric ID from
    the dbXrefs column.
    """

    def parse(self, data: bytes) -> list[GeneInfoRecord]:
        """Parse gzip-compressed gene_info data.

        Args:
            data: Raw gzip bytes from NCBI.

        Returns:
            List of ``GeneInfoRecord`` instances for accepted tax IDs.
        """
        decompressed = gzip.decompress(data).decode("utf-8")
        lines = decompressed.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[GeneInfoRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")

        for cols in reader:
            if len(cols) < 15:
                continue

            tax_id = cols[0].strip()
            eg_id = cols[1].strip()

            if tax_id not in ACCEPTED_TAX_IDS:
                continue

            if eg_id in SKIP_EG_IDS:
                continue

            hgnc_match = HGNC_RE.search(cols[5])
            hgnc_id = int(hgnc_match.group(1)) if hgnc_match else 0

            records.append(
                GeneInfoRecord(
                    gi_tax_id=tax_id,
                    gi_eg_id=eg_id,
                    gi_sym=cols[2].strip(),
                    gi_locustag=self._clean(cols[3]),
                    gi_synonyms=self._clean(cols[4]),
                    gi_dbxrefs=self._clean(cols[5]),
                    gi_chrom=self._clean(cols[6]),
                    gi_map_location=self._clean(cols[7]),
                    gi_description=self._clean(cols[8]),
                    gi_type_of_gene=self._clean(cols[9]),
                    gi_sym_from_nome_auth=self._clean(cols[10]),
                    gi_full_name_from_nome_auth=self._clean(cols[11]),
                    gi_nome_status=self._clean(cols[12]),
                    gi_other_designations=self._clean(cols[13]),
                    gi_modification_date=self._clean(cols[14]),
                    gi_hgnc_id=hgnc_id,
                )
            )

        logger.info(
            "gene_info_parsed",
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
