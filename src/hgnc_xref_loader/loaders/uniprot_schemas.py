"""UniProt 4-table staging schemas and parser configuration.

Defines the column schemas for the four UniProt staging tables
(uniprot_update, uniprot_has_hgnc_update, uniprot_has_ncbi_gene_update,
uniprot_has_ec_update) derived from the Perl
HGNC::DB::PostgreSQL::Genew4::Load::Table::UniProt reference.

TSV field order from the UniProt REST API stream endpoint:
accession, reviewed, entry_id, protein_name, gene_primary,
xref_hgnc, ec, xref_geneid
"""

from __future__ import annotations

from dataclasses import dataclass

UNIPROT_HEADER_LINES = 19

UNIPROT_TSV_FIELDS = [
    "accession",
    "reviewed",
    "entry_id",
    "protein_name",
    "gene_primary",
    "xref_hgnc",
    "ec",
    "xref_geneid",
]

UNIPROT_REST_URL = (
    "https://rest.uniprot.org/uniprotkb/stream"
    "?query=active:true+AND+organism_id:9606"
    "&format=tsv"
    "&fields=accession,reviewed,id,protein_name,gene_primary,xref_hgnc,ec,xref_geneid"
    "&sort=protein_name%20asc"
)


@dataclass(frozen=True)
class UniprotMainSchema:
    """Schema definition for the main uniprot_update staging table."""

    staging_table: str = "uniprot_update"
    production_table: str = "uniprot"
    columns: tuple[str, ...] = (
        "unip_acc",
        "unip_status",
        "unip_entry_name",
        "unip_prot_name",
        "unip_sym",
    )


@dataclass(frozen=True)
class UniprotMainStagingRow:
    """A single row for the main uniprot_update staging table.

    Attributes:
        unip_acc: UniProt accession (e.g. ``P00750``).
        unip_status: Review status (``reviewed`` or ``unreviewed``).
        unip_entry_name: UniProt entry name (e.g. ``UROT_HUMAN``).
        unip_prot_name: Protein name, cleaned before ``(`` or ``[``.
        unip_sym: Primary gene symbol.
    """

    unip_acc: str
    unip_status: str
    unip_entry_name: str
    unip_prot_name: str
    unip_sym: str

    def to_dict(self) -> dict[str, str]:
        return {
            "unip_acc": self.unip_acc,
            "unip_status": self.unip_status,
            "unip_entry_name": self.unip_entry_name,
            "unip_prot_name": self.unip_prot_name,
            "unip_sym": self.unip_sym,
        }


@dataclass(frozen=True)
class UniprotHasHgncSchema:
    """Schema definition for the uniprot_has_hgnc_update junction staging table."""

    staging_table: str = "uniprot_has_hgnc_update"
    production_table: str = "uniprot_has_hgnc"
    columns: tuple[str, ...] = ("unip_acc", "hgnc_id")


@dataclass(frozen=True)
class UniprotHgncStagingRow:
    """A single row for the uniprot_has_hgnc_update junction table.

    Attributes:
        unip_acc: UniProt accession.
        hgnc_id: HGNC numeric ID (prefix stripped).
    """

    unip_acc: str
    hgnc_id: int

    def to_dict(self) -> dict[str, str | int]:
        return {"unip_acc": self.unip_acc, "hgnc_id": self.hgnc_id}


@dataclass(frozen=True)
class UniprotHasNcbiGeneSchema:
    """Schema definition for the uniprot_has_ncbi_gene_update junction staging table."""

    staging_table: str = "uniprot_has_ncbi_gene_update"
    production_table: str = "uniprot_has_ncbi_gene"
    columns: tuple[str, ...] = ("unip_acc", "ncbi_gene_id")


@dataclass(frozen=True)
class UniprotNcbiGeneStagingRow:
    """A single row for the uniprot_has_ncbi_gene_update junction table.

    Attributes:
        unip_acc: UniProt accession.
        ncbi_gene_id: NCBI Entrez Gene ID.
    """

    unip_acc: str
    ncbi_gene_id: int

    def to_dict(self) -> dict[str, str | int]:
        return {"unip_acc": self.unip_acc, "ncbi_gene_id": self.ncbi_gene_id}


@dataclass(frozen=True)
class UniprotHasEcSchema:
    """Schema definition for the uniprot_has_ec_update junction staging table."""

    staging_table: str = "uniprot_has_ec_update"
    production_table: str = "uniprot_has_ec"
    columns: tuple[str, ...] = ("unip_acc", "ec_id")


@dataclass(frozen=True)
class UniprotEcStagingRow:
    """A single row for the uniprot_has_ec_update junction table.

    Attributes:
        unip_acc: UniProt accession.
        ec_id: EC number (prefix stripped, e.g. ``3.4.21.73``).
    """

    unip_acc: str
    ec_id: str

    def to_dict(self) -> dict[str, str]:
        return {"unip_acc": self.unip_acc, "ec_id": self.ec_id}
