"""Tests for UniProt TSV parser.

Validates parsing of the UniProt REST API TSV stream into the four
staging table row types: main, has_hgnc, has_ncbi_gene, has_ec.
"""

from __future__ import annotations

import pytest

from hgnc_xref_loader.loaders.uniprot_parser import (
    UniprotParsedBatch,
    UniprotTsvParser,
)


def _make_tsv(rows: list[str]) -> bytes:
    header = (
        "Entry\tStatus\tEntry Name\tProtein names\tGene Names (primary)\t"
        "Cross-reference (HGNC)\tEC number\tCross-reference (GeneID)"
    )
    lines = ["comment line"] * 19 + [header] + rows
    return "\n".join(lines).encode("utf-8")


SAMPLE_ROW = (
    "P00750\treviewed\tUROT_HUMAN\tUrokinase-type plasminogen activator "
    "(EC 3.4.21.73)\tPLAU\tHGNC:HGNC:9052;HGNC:HGNC:9999\t"
    "3.4.21.73;3.4.21.74\t1234;5678"
)


class TestUniprotTsvParserInit:
    """Test parser initialisation."""

    def test_default_header_lines(self) -> None:
        parser = UniprotTsvParser()
        assert parser.header_lines == 19

    def test_custom_header_lines(self) -> None:
        parser = UniprotTsvParser(header_lines=5)
        assert parser.header_lines == 5


class TestUniprotTsvParserBasic:
    """Test basic single-row parsing."""

    def test_parse_single_row_main(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT_HUMAN\tPlasminogen activator\tPLAU\t\t\t"])
        batch = parser.parse(data)

        assert len(batch.main_rows) == 1
        row = batch.main_rows[0]
        assert row.unip_acc == "P00750"
        assert row.unip_status == "reviewed"
        assert row.unip_entry_name == "UROT_HUMAN"
        assert row.unip_prot_name == "Plasminogen activator"
        assert row.unip_sym == "PLAU"

    def test_parse_skips_header_lines(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT_HUMAN\tProt\tPLAU\t\t\t"])
        batch = parser.parse(data)

        assert len(batch.main_rows) == 1


class TestUniprotProteinNameCleaning:
    """Test protein name extraction before ( or [."""

    def test_strip_before_parenthesis(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT_HUMAN\tUrokinase activator (EC 3.4.21)\tPLAU\t\t\t"])
        batch = parser.parse(data)

        assert batch.main_rows[0].unip_prot_name == "Urokinase activator"

    def test_strip_before_bracket(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT_HUMAN\tMy protein [Fragment]\tPLAU\t\t\t"])
        batch = parser.parse(data)

        assert batch.main_rows[0].unip_prot_name == "My protein"

    def test_no_parens_or_brackets(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT_HUMAN\tSimple name\tPLAU\t\t\t"])
        batch = parser.parse(data)

        assert batch.main_rows[0].unip_prot_name == "Simple name"


class TestUniprotHgncMapping:
    """Test xref_hgnc multi-value splitting and HGNC: prefix stripping."""

    def test_single_hgnc_id(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\tHGNC:9052\t\t"])
        batch = parser.parse(data)

        assert len(batch.hgnc_rows) == 1
        assert batch.hgnc_rows[0].hgnc_id == 9052
        assert batch.hgnc_rows[0].unip_acc == "P00750"

    def test_multiple_hgnc_ids(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\tHGNC:9052;HGNC:9999\t\t"])
        batch = parser.parse(data)

        assert len(batch.hgnc_rows) == 2
        assert batch.hgnc_rows[0].hgnc_id == 9052
        assert batch.hgnc_rows[1].hgnc_id == 9999

    def test_empty_hgnc_field(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\t\t\t"])
        batch = parser.parse(data)

        assert len(batch.hgnc_rows) == 0

    def test_hgnc_double_prefix(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\tHGNC:HGNC:9052\t\t"])
        batch = parser.parse(data)

        assert len(batch.hgnc_rows) == 1
        assert batch.hgnc_rows[0].hgnc_id == 9052


class TestUniprotNcbiGeneMapping:
    """Test xref_geneid multi-value splitting."""

    def test_single_ncbi_gene_id(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\t\t\t1234"])
        batch = parser.parse(data)

        assert len(batch.ncbi_gene_rows) == 1
        assert batch.ncbi_gene_rows[0].ncbi_gene_id == 1234

    def test_multiple_ncbi_gene_ids(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\t\t\t1234;5678"])
        batch = parser.parse(data)

        assert len(batch.ncbi_gene_rows) == 2
        assert batch.ncbi_gene_rows[0].ncbi_gene_id == 1234
        assert batch.ncbi_gene_rows[1].ncbi_gene_id == 5678


class TestUniprotEcMapping:
    """Test ec multi-value splitting and EC: prefix stripping."""

    def test_single_ec(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\t\t3.4.21.73\t"])
        batch = parser.parse(data)

        assert len(batch.ec_rows) == 1
        assert batch.ec_rows[0].ec_id == "3.4.21.73"

    def test_multiple_ecs(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\t\t3.4.21.73;3.4.21.74\t"])
        batch = parser.parse(data)

        assert len(batch.ec_rows) == 2
        assert batch.ec_rows[0].ec_id == "3.4.21.73"
        assert batch.ec_rows[1].ec_id == "3.4.21.74"

    def test_ec_with_prefix(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv(["P00750\treviewed\tUROT\tProt\tPLAU\t\tEC:3.4.21.73\t"])
        batch = parser.parse(data)

        assert len(batch.ec_rows) == 1
        assert batch.ec_rows[0].ec_id == "3.4.21.73"


class TestUniprotMultiRow:
    """Test parsing multiple rows."""

    def test_multiple_rows(self) -> None:
        parser = UniprotTsvParser()
        rows = [
            "P00750\treviewed\tUROT_HUMAN\tProt A\tPLAU\tHGNC:9052\t\t",
            "P31946\treviewed\t1433B_HUMAN\tProt B\tYWHAB\tHGNC:12853\t\t99",
        ]
        data = _make_tsv(rows)
        batch = parser.parse(data)

        assert len(batch.main_rows) == 2
        assert batch.main_rows[0].unip_acc == "P00750"
        assert batch.main_rows[1].unip_acc == "P31946"
        assert len(batch.hgnc_rows) == 2
        assert len(batch.ncbi_gene_rows) == 1

    def test_full_row_all_fields(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv([SAMPLE_ROW])
        batch = parser.parse(data)

        assert len(batch.main_rows) == 1
        assert batch.main_rows[0].unip_prot_name == "Urokinase-type plasminogen activator"
        assert len(batch.hgnc_rows) == 2
        assert len(batch.ec_rows) == 2
        assert len(batch.ncbi_gene_rows) == 2


class TestUniprotParsedBatch:
    """Test the parsed batch summary."""

    def test_total_rows(self) -> None:
        parser = UniprotTsvParser()
        data = _make_tsv([SAMPLE_ROW])
        batch = parser.parse(data)

        assert batch.total_main == 1
        assert batch.total_hgnc == 2
        assert batch.total_ec == 2
        assert batch.total_ncbi_gene == 2
