"""Omim2Gene TSV parser for OMIM mim2gene.txt data.

Parses the OMIM mim2gene.txt file with tab-separated values.

Staging table columns:
    m2g_mim_number, m2g_type, m2g_eg_id, m2g_app_sym, m2g_ensg
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1


@dataclass(frozen=True)
class Omim2GeneRecord:
    """A single omim2gene staging row.

    Attributes:
        m2g_mim_number: OMIM MIM number.
        m2g_type: Entry type (gene, phenotype, etc).
        m2g_eg_id: Entrez Gene ID.
        m2g_app_sym: Approved gene symbol.
        m2g_ensg: Ensembl gene ID.
    """

    m2g_mim_number: str
    m2g_type: str
    m2g_eg_id: str
    m2g_app_sym: str
    m2g_ensg: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "m2g_mim_number": self.m2g_mim_number,
            "m2g_type": self.m2g_type,
            "m2g_eg_id": self.m2g_eg_id,
            "m2g_app_sym": self.m2g_app_sym,
            "m2g_ensg": self.m2g_ensg,
        }


class Omim2GeneParser:
    """Parse OMIM mim2gene.txt into Omim2GeneRecord staging rows."""

    def parse(self, data: bytes) -> list[Omim2GeneRecord]:
        """Parse OMIM mim2gene data.

        Args:
            data: Raw bytes from OMIM.

        Returns:
            List of ``Omim2GeneRecord`` instances.
        """
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[Omim2GeneRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")

        for cols in reader:
            if len(cols) < 5:
                continue

            records.append(
                Omim2GeneRecord(
                    m2g_mim_number=self._clean(cols[0]),
                    m2g_type=self._clean(cols[1]),
                    m2g_eg_id=self._clean(cols[2]),
                    m2g_app_sym=self._clean(cols[3]),
                    m2g_ensg=self._clean(cols[4]),
                )
            )

        logger.info(
            "omim2gene_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _clean(val: str) -> str:
        """Clean a TSV field value."""
        stripped = val.strip()
        return "" if stripped == "-" else stripped
