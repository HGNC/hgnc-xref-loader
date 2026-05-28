"""RefSeq catalog TSV parser for NCBI RefSeq-release*.catalog.gz data.

Parses the gzip-compressed NCBI RefSeq catalog file, filtering to accepted
tax IDs (9606 human, 10090 mouse, 10116 rat).

Staging table columns:
    rfc_tax_id, rfc_species, rfc_refseq_id, rfc_release, rfc_status, rfc_length
"""

from __future__ import annotations

import csv
import gzip
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

ACCEPTED_TAX_IDS = {"9606", "10090", "10116"}


@dataclass(frozen=True)
class RefseqCatalogRecord:
    """A single refseq_catalog staging row.

    Attributes:
        rfc_tax_id: NCBI taxonomy ID.
        rfc_species: Species name.
        rfc_refseq_id: RefSeq accession.
        rfc_release: Release version.
        rfc_status: Status (e.g. REVIEWED).
        rfc_length: Sequence length.
    """

    rfc_tax_id: str
    rfc_species: str
    rfc_refseq_id: str
    rfc_release: str
    rfc_status: str
    rfc_length: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "rfc_tax_id": self.rfc_tax_id,
            "rfc_species": self.rfc_species,
            "rfc_refseq_id": self.rfc_refseq_id,
            "rfc_release": self.rfc_release,
            "rfc_status": self.rfc_status,
            "rfc_length": self.rfc_length,
        }


class RefseqCatalogParser:
    """Parse NCBI RefSeq-release*.catalog.gz into RefseqCatalogRecord rows.

    Filters by accepted tax IDs (human, mouse, rat).
    """

    def parse(self, data: bytes) -> list[RefseqCatalogRecord]:
        """Parse gzip-compressed refseq catalog data.

        Args:
            data: Raw gzip bytes from NCBI.

        Returns:
            List of ``RefseqCatalogRecord`` instances for accepted tax IDs.
        """
        decompressed = gzip.decompress(data).decode("utf-8")
        lines = decompressed.splitlines()

        records: list[RefseqCatalogRecord] = []
        reader = csv.reader(lines, delimiter="\t")

        for cols in reader:
            if len(cols) < 6:
                continue

            tax_id = cols[0].strip()
            if tax_id not in ACCEPTED_TAX_IDS:
                continue

            records.append(
                RefseqCatalogRecord(
                    rfc_tax_id=tax_id,
                    rfc_species=self._clean(cols[1]),
                    rfc_refseq_id=self._clean(cols[2]),
                    rfc_release=self._clean(cols[3]),
                    rfc_status=self._clean(cols[4]),
                    rfc_length=self._clean(cols[5]),
                )
            )

        logger.info(
            "refseq_catalog_parsed",
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
