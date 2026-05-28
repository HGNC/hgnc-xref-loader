"""Tests for UniProt schema design and parser configuration.

Validates the 4-table staging schema definitions and parser configuration
derived from the Perl HGNC::DB::PostgreSQL::Genew4::Load::Table::UniProt
reference implementation.
"""

from __future__ import annotations

import pytest


class TestUniprotSchemaImports:
    """Verify schema definitions can be imported."""

    def test_import_uniprot_schemas(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import (
            UniprotEcStagingRow,
            UniprotHasEcSchema,
            UniprotHasHgncSchema,
            UniprotHasNcbiGeneSchema,
            UniprotHgncStagingRow,
            UniprotMainSchema,
            UniprotMainStagingRow,
            UniprotNcbiGeneStagingRow,
        )

        assert UniprotMainSchema is not None
        assert UniprotHasHgncSchema is not None
        assert UniprotHasNcbiGeneSchema is not None
        assert UniprotHasEcSchema is not None


class TestUniprotMainSchema:
    """Verify the main uniprot_update staging table schema."""

    def test_main_schema_has_5_columns(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotMainSchema

        assert list(UniprotMainSchema.columns) == [
            "unip_acc",
            "unip_status",
            "unip_entry_name",
            "unip_prot_name",
            "unip_sym",
        ]

    def test_main_schema_table_name(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotMainSchema

        assert UniprotMainSchema.staging_table == "uniprot_update"
        assert UniprotMainSchema.production_table == "uniprot"

    def test_main_staging_row_to_dict(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotMainStagingRow

        row = UniprotMainStagingRow(
            unip_acc="P00750",
            unip_status="reviewed",
            unip_entry_name="UROT_HUMAN",
            unip_prot_name="Urokinase-type plasminogen activator",
            unip_sym="PLAU",
        )
        d = row.to_dict()
        assert d["unip_acc"] == "P00750"
        assert d["unip_prot_name"] == "Urokinase-type plasminogen activator"
        assert len(d) == 5


class TestUniprotHasHgncSchema:
    """Verify the uniprot_has_hgnc_update junction table schema."""

    def test_hgnc_schema_has_2_columns(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotHasHgncSchema

        assert list(UniprotHasHgncSchema.columns) == ["unip_acc", "hgnc_id"]

    def test_hgnc_schema_table_name(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotHasHgncSchema

        assert UniprotHasHgncSchema.staging_table == "uniprot_has_hgnc_update"

    def test_hgnc_staging_row(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotHgncStagingRow

        row = UniprotHgncStagingRow(unip_acc="P00750", hgnc_id=9052)
        d = row.to_dict()
        assert d["unip_acc"] == "P00750"
        assert d["hgnc_id"] == 9052


class TestUniprotHasNcbiGeneSchema:
    """Verify the uniprot_has_ncbi_gene_update junction table schema."""

    def test_ncbi_gene_schema_has_2_columns(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotHasNcbiGeneSchema

        assert list(UniprotHasNcbiGeneSchema.columns) == ["unip_acc", "ncbi_gene_id"]

    def test_ncbi_gene_schema_table_name(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotHasNcbiGeneSchema

        assert UniprotHasNcbiGeneSchema.staging_table == "uniprot_has_ncbi_gene_update"


class TestUniprotHasEcSchema:
    """Verify the uniprot_has_ec_update junction table schema."""

    def test_ec_schema_has_2_columns(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotHasEcSchema

        assert list(UniprotHasEcSchema.columns) == ["unip_acc", "ec_id"]

    def test_ec_schema_table_name(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotHasEcSchema

        assert UniprotHasEcSchema.staging_table == "uniprot_has_ec_update"

    def test_ec_staging_row(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UniprotEcStagingRow

        row = UniprotEcStagingRow(unip_acc="P00750", ec_id="3.4.21.73")
        d = row.to_dict()
        assert d["ec_id"] == "3.4.21.73"


class TestUniprotParserConfig:
    """Verify parser configuration matches the Perl reference."""

    def test_header_lines_to_skip(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UNIPROT_HEADER_LINES

        assert UNIPROT_HEADER_LINES == 19

    def test_tsv_field_order(self) -> None:
        from hgnc_xref_loader.loaders.uniprot_schemas import UNIPROT_TSV_FIELDS

        assert UNIPROT_TSV_FIELDS == [
            "accession",
            "reviewed",
            "entry_id",
            "protein_name",
            "gene_primary",
            "xref_hgnc",
            "ec",
            "xref_geneid",
        ]
