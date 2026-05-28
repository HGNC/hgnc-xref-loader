"""RGD Orthologs TSV parser for RGD_ORTHOLOGS.txt data.

Parses the RGD orthologs TSV file, stripping HGNC: prefix from
the human ortholog HGNC ID column.

Staging table columns:
    rgdo_rat_gene_symbol, rgdo_rat_gene_rgd_id, rgdo_rat_gene_entrez_gene_id,
    rgdo_human_ortholog_symbol, rgdo_human_ortholog_rgd, rgdo_human_ortholog_entrez,
    rgdo_human_ortholog_source, rgdo_mouse_ortholog_symbol, rgdo_mouse_ortholog_rgd,
    rgdo_mouse_ortholog_entrez, rgdo_mouse_ortholog_mgi, rgdo_mouse_ortholog_source,
    rgdo_human_ortholog_hgnc_id
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1


@dataclass(frozen=True)
class RgdOrthologsRecord:
    """A single rgd_orthologs staging row.

    Attributes:
        rgdo_rat_gene_symbol: Rat gene symbol.
        rgdo_rat_gene_rgd_id: Rat RGD ID.
        rgdo_rat_gene_entrez_gene_id: Rat Entrez Gene ID.
        rgdo_human_ortholog_symbol: Human ortholog symbol.
        rgdo_human_ortholog_rgd: Human ortholog RGD ID.
        rgdo_human_ortholog_entrez: Human ortholog Entrez Gene ID.
        rgdo_human_ortholog_source: Ortholog source.
        rgdo_mouse_ortholog_symbol: Mouse ortholog symbol.
        rgdo_mouse_ortholog_rgd: Mouse ortholog RGD ID.
        rgdo_mouse_ortholog_entrez: Mouse ortholog Entrez Gene ID.
        rgdo_mouse_ortholog_mgi: Mouse ortholog MGI ID.
        rgdo_mouse_ortholog_source: Mouse ortholog source.
        rgdo_human_ortholog_hgnc_id: Human ortholog HGNC ID (stripped).
    """

    rgdo_rat_gene_symbol: str
    rgdo_rat_gene_rgd_id: str
    rgdo_rat_gene_entrez_gene_id: str
    rgdo_human_ortholog_symbol: str
    rgdo_human_ortholog_rgd: str
    rgdo_human_ortholog_entrez: str
    rgdo_human_ortholog_source: str
    rgdo_mouse_ortholog_symbol: str
    rgdo_mouse_ortholog_rgd: str
    rgdo_mouse_ortholog_entrez: str
    rgdo_mouse_ortholog_mgi: str
    rgdo_mouse_ortholog_source: str
    rgdo_human_ortholog_hgnc_id: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "rgdo_rat_gene_symbol": self.rgdo_rat_gene_symbol,
            "rgdo_rat_gene_rgd_id": self.rgdo_rat_gene_rgd_id,
            "rgdo_rat_gene_entrez_gene_id": self.rgdo_rat_gene_entrez_gene_id,
            "rgdo_human_ortholog_symbol": self.rgdo_human_ortholog_symbol,
            "rgdo_human_ortholog_rgd": self.rgdo_human_ortholog_rgd,
            "rgdo_human_ortholog_entrez": self.rgdo_human_ortholog_entrez,
            "rgdo_human_ortholog_source": self.rgdo_human_ortholog_source,
            "rgdo_mouse_ortholog_symbol": self.rgdo_mouse_ortholog_symbol,
            "rgdo_mouse_ortholog_rgd": self.rgdo_mouse_ortholog_rgd,
            "rgdo_mouse_ortholog_entrez": self.rgdo_mouse_ortholog_entrez,
            "rgdo_mouse_ortholog_mgi": self.rgdo_mouse_ortholog_mgi,
            "rgdo_mouse_ortholog_source": self.rgdo_mouse_ortholog_source,
            "rgdo_human_ortholog_hgnc_id": self.rgdo_human_ortholog_hgnc_id,
        }


class RgdOrthologsParser:
    """Parse RGD orthologs TSV into RgdOrthologsRecord staging rows."""

    def parse(self, data: bytes) -> list[RgdOrthologsRecord]:
        """Parse RGD orthologs TSV data.

        Args:
            data: Raw TSV bytes from RGD.

        Returns:
            List of ``RgdOrthologsRecord`` instances.
        """
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[RgdOrthologsRecord] = []
        reader = csv.reader(lines[HEADER_LINES:], delimiter="\t")

        for cols in reader:
            if len(cols) < 13:
                continue

            hgnc_id = self._clean(cols[12]).replace("HGNC:", "")

            records.append(
                RgdOrthologsRecord(
                    rgdo_rat_gene_symbol=self._clean(cols[0]),
                    rgdo_rat_gene_rgd_id=self._clean(cols[1]),
                    rgdo_rat_gene_entrez_gene_id=self._clean(cols[2]),
                    rgdo_human_ortholog_symbol=self._clean(cols[3]),
                    rgdo_human_ortholog_rgd=self._clean(cols[4]),
                    rgdo_human_ortholog_entrez=self._clean(cols[5]),
                    rgdo_human_ortholog_source=self._clean(cols[6]),
                    rgdo_mouse_ortholog_symbol=self._clean(cols[7]),
                    rgdo_mouse_ortholog_rgd=self._clean(cols[8]),
                    rgdo_mouse_ortholog_entrez=self._clean(cols[9]),
                    rgdo_mouse_ortholog_mgi=self._clean(cols[10]),
                    rgdo_mouse_ortholog_source=self._clean(cols[11]),
                    rgdo_human_ortholog_hgnc_id=hgnc_id,
                )
            )

        logger.info(
            "rgd_orthologs_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _clean(val: str) -> str:
        """Clean a TSV field value."""
        stripped = val.strip()
        return "" if stripped == "-" else stripped
