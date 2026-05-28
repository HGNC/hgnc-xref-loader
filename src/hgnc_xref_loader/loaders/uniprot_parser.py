"""UniProt TSV parser for the 4-table staging pipeline.

Parses the UniProt REST API TSV stream into four sets of staging rows:
main uniprot, uniprot_has_hgnc, uniprot_has_ncbi_gene, and uniprot_has_ec.

Handles:
- Skipping 19 comment/header lines before the column header.
- Semicolon-delimited multi-value fields (xref_hgnc, ec, xref_geneid).
- Stripping ``HGNC:`` prefix from HGNC IDs and ``EC:`` from EC numbers.
- Cleaning protein names by truncating at ``(`` or ``[``.
"""

from __future__ import annotations

import csv
import io
import logging
import re

from hgnc_xref_loader.loaders.uniprot_schemas import (
    UNIPROT_TSV_FIELDS,
    UniprotEcStagingRow,
    UniprotHgncStagingRow,
    UniprotMainStagingRow,
    UniprotNcbiGeneStagingRow,
)

logger = logging.getLogger(__name__)

_PROTO_CLEAN_RE = re.compile(r"\s*[(\[]")


class UniprotParsedBatch:
    """Aggregation of parsed rows across all four staging tables.

    Attributes:
        main_rows: Rows for the main uniprot_update table.
        hgnc_rows: Rows for the uniprot_has_hgnc_update junction table.
        ncbi_gene_rows: Rows for the uniprot_has_ncbi_gene_update junction table.
        ec_rows: Rows for the uniprot_has_ec_update junction table.
    """

    def __init__(self) -> None:
        self.main_rows: list[UniprotMainStagingRow] = []
        self.hgnc_rows: list[UniprotHgncStagingRow] = []
        self.ncbi_gene_rows: list[UniprotNcbiGeneStagingRow] = []
        self.ec_rows: list[UniprotEcStagingRow] = []

    @property
    def total_main(self) -> int:
        return len(self.main_rows)

    @property
    def total_hgnc(self) -> int:
        return len(self.hgnc_rows)

    @property
    def total_ncbi_gene(self) -> int:
        return len(self.ncbi_gene_rows)

    @property
    def total_ec(self) -> int:
        return len(self.ec_rows)


class UniprotTsvParser:
    """Parse UniProt REST API TSV into 4-table staging row batches.

    Args:
        header_lines: Number of comment/header lines to skip before the
            column header row.
    """

    def __init__(self, header_lines: int = 19) -> None:
        self.header_lines = header_lines

    def parse(self, data: bytes) -> UniprotParsedBatch:
        """Parse raw TSV bytes into a structured batch.

        Args:
            data: Raw TSV content from the UniProt REST API.

        Returns:
            A ``UniprotParsedBatch`` with rows for all four staging tables.
        """
        batch = UniprotParsedBatch()
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= self.header_lines:
            return batch

        header_line = lines[self.header_lines]
        reader = csv.DictReader(io.StringIO("\n".join(lines[self.header_lines + 1 :])), fieldnames=header_line.split("\t"), delimiter="\t")

        for row in reader:
            self._parse_row(row, batch)

        logger.info(
            "uniprot_parse_complete",
            extra={
                "event": "uniprot_parse_complete",
                "main": batch.total_main,
                "hgnc": batch.total_hgnc,
                "ncbi_gene": batch.total_ncbi_gene,
                "ec": batch.total_ec,
            },
        )

        return batch

    def _parse_row(self, row: dict[str, str], batch: UniprotParsedBatch) -> None:
        """Parse a single TSV row into staging rows.

        Args:
            row: A dict mapping TSV column names to values.
            batch: The batch to append rows to.
        """
        accession = row.get("Entry", "").strip()
        if not accession:
            return

        status = row.get("Status", "").strip()
        entry_name = row.get("Entry Name", "").strip()
        raw_prot_name = row.get("Protein names", "").strip()
        gene_primary = row.get("Gene Names (primary)", "").strip()

        prot_name = self._clean_protein_name(raw_prot_name)

        batch.main_rows.append(
            UniprotMainStagingRow(
                unip_acc=accession,
                unip_status=status,
                unip_entry_name=entry_name,
                unip_prot_name=prot_name,
                unip_sym=gene_primary,
            )
        )

        self._parse_hgnc(accession, row, batch)
        self._parse_ncbi_gene(accession, row, batch)
        self._parse_ec(accession, row, batch)

    def _parse_hgnc(self, accession: str, row: dict[str, str], batch: UniprotParsedBatch) -> None:
        """Extract HGNC ID junction rows from the xref_hgnc field.

        Args:
            accession: UniProt accession.
            row: TSV row dict.
            batch: Batch to append to.
        """
        raw = row.get("Cross-reference (HGNC)", "").strip()
        if not raw:
            return

        for part in raw.split(";"):
            val = part.strip()
            if not val:
                continue
            while val.startswith("HGNC:"):
                val = val[5:]
            if val.isdigit():
                batch.hgnc_rows.append(
                    UniprotHgncStagingRow(unip_acc=accession, hgnc_id=int(val))
                )

    def _parse_ncbi_gene(self, accession: str, row: dict[str, str], batch: UniprotParsedBatch) -> None:
        """Extract NCBI Gene ID junction rows from the xref_geneid field.

        Args:
            accession: UniProt accession.
            row: TSV row dict.
            batch: Batch to append to.
        """
        raw = row.get("Cross-reference (GeneID)", "").strip()
        if not raw:
            return

        for part in raw.split(";"):
            val = part.strip()
            if val.isdigit():
                batch.ncbi_gene_rows.append(
                    UniprotNcbiGeneStagingRow(unip_acc=accession, ncbi_gene_id=int(val))
                )

    def _parse_ec(self, accession: str, row: dict[str, str], batch: UniprotParsedBatch) -> None:
        """Extract EC number junction rows from the ec field.

        Args:
            accession: UniProt accession.
            row: TSV row dict.
            batch: Batch to append to.
        """
        raw = row.get("EC number", "").strip()
        if not raw:
            return

        for part in raw.split(";"):
            val = part.strip()
            if val.startswith("EC:"):
                val = val[3:]
            if val:
                batch.ec_rows.append(
                    UniprotEcStagingRow(unip_acc=accession, ec_id=val)
                )

    @staticmethod
    def _clean_protein_name(raw: str) -> str:
        """Strip parenthetical/bracketed suffixes from a protein name.

        Args:
            raw: Raw protein name from UniProt.

        Returns:
            Cleaned protein name with trailing ``(...)`` or ``[...]`` removed.
        """
        match = _PROTO_CLEAN_RE.search(raw)
        if match:
            return raw[: match.start()].strip()
        return raw
