"""Tests for CCDS TSV parser.

Validates parsing of CCDS.current.txt into typed, validated records
suitable for bulk loading into the ccds_update staging table.
"""

from __future__ import annotations

import io

import pytest

from hgnc_xref_loader.loaders.ccds_parser import (
    CcdsParseError,
    CcdsRecord,
    CcdsTsvParser,
)

SAMPLE_HEADER = "#chromosome\taccession\tversion\tsymbol\tncbi_gene_id\tccds_id\tstatus\tstrand\tfrom\tto\tlocations\tmatch_type"

SAMPLE_DATA_ROWS = [
    "chr1\tNC_000001.11\t1\tA1BG\t1\tCCDS1.1\tPublic\t-\t11873\t11873\t;\tNotAvailable",
    "chr1\tNC_000001.11\t1\tA1CF\t29974\tCCDS2.2\tPublic\t+\t11873\t12000\t;\tNotAvailable",
    "chr10\tNC_000010.11\t1\tADA\t100\tCCDS3.1\tWithdrawn\t+\t50000\t60000\t;\tNotAvailable",
    "chrX\tNC_000023.11\t1\tDDX3X\t1654\tCCDS4.1\tPublic,Definition pending\t-\t100000\t200000\t;\tNotAvailable",
]

MINIMAL_ROW = "chr5\tNC_000005.10\t1\tGENE\t999\tCCDS99.1\tPublic\t+\t1\t100\t;\tNotAvailable"


class TestCcdsRecord:
    """Verify CcdsRecord data class."""

    def test_create_valid_record(self) -> None:
        record = CcdsRecord(
            chromosome="chr1",
            accession="NC_000001.11",
            symbol="A1BG",
            ncbi_gene_id="1",
            ccds_id="CCDS1.1",
            status="Public",
            strand="-",
            start="11873",
            end="11873",
            locations=";",
            match_type="NotAvailable",
        )
        assert record.chromosome == "chr1"
        assert record.ccds_id == "CCDS1.1"

    def test_record_fields_match_staging_schema(self) -> None:
        record = CcdsRecord(
            chromosome="chr1",
            accession="NC_000001.11",
            symbol="A1BG",
            ncbi_gene_id="1",
            ccds_id="CCDS1.1",
            status="Public",
            strand="-",
            start="11873",
            end="11873",
            locations=";",
            match_type="NotAvailable",
        )
        staging_dict = record.to_staging_dict()
        assert "ccds_chrom" in staging_dict
        assert "ccds_acc" in staging_dict
        assert "ccds_sym" in staging_dict
        assert "ccds_eg_id" in staging_dict
        assert "ccds_id" in staging_dict
        assert "ccds_status" in staging_dict
        assert "ccds_strand" in staging_dict
        assert "ccds_from" in staging_dict
        assert "ccds_to" in staging_dict
        assert "ccds_locations" in staging_dict
        assert "ccds_match_type" in staging_dict

    def test_dash_values_become_empty(self) -> None:
        record = CcdsRecord(
            chromosome="chr1",
            accession="-",
            symbol="-",
            ncbi_gene_id="1",
            ccds_id="CCDS1.1",
            status="Public",
            strand="-",
            start="-",
            end="-",
            locations="-",
            match_type="-",
        )
        d = record.to_staging_dict()
        assert d["ccds_acc"] == ""
        assert d["ccds_sym"] == ""
        assert d["ccds_from"] == ""
        assert d["ccds_to"] == ""
        assert d["ccds_locations"] == ""
        assert d["ccds_match_type"] == ""


class TestCcdsTsvParser:
    """Verify TSV parsing, header skip, and field normalization."""

    def _make_tsv(self, lines: list[str]) -> str:
        return "\n".join(lines) + "\n"

    def test_parse_skips_single_header(self) -> None:
        tsv = self._make_tsv([SAMPLE_HEADER] + SAMPLE_DATA_ROWS)
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert len(records) == 4

    def test_parse_empty_input(self) -> None:
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(""))
        assert records == []

    def test_parse_header_only(self) -> None:
        tsv = self._make_tsv([SAMPLE_HEADER])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert records == []

    def test_parse_extracts_correct_fields(self) -> None:
        tsv = self._make_tsv([SAMPLE_HEADER, SAMPLE_DATA_ROWS[0]])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert len(records) == 1
        rec = records[0]
        assert rec.chromosome == "chr1"
        assert rec.accession == "NC_000001.11"
        assert rec.symbol == "A1BG"
        assert rec.ncbi_gene_id == "1"
        assert rec.ccds_id == "CCDS1.1"
        assert rec.status == "Public"
        assert rec.strand == "-"
        assert rec.start == "11873"
        assert rec.end == "11873"

    def test_parse_handles_withdrawn_status(self) -> None:
        tsv = self._make_tsv([SAMPLE_HEADER, SAMPLE_DATA_ROWS[2]])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert records[0].status == "Withdrawn"

    def test_parse_handles_composite_status(self) -> None:
        tsv = self._make_tsv([SAMPLE_HEADER, SAMPLE_DATA_ROWS[3]])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert records[0].status == "Public,Definition pending"

    def test_parse_raw_bytes(self) -> None:
        raw = self._make_tsv([SAMPLE_HEADER, MINIMAL_ROW]).encode("utf-8")
        parser = CcdsTsvParser()
        records = parser.parse_bytes(raw)
        assert len(records) == 1
        assert records[0].ccds_id == "CCDS99.1"

    def test_parse_skips_malformed_rows(self) -> None:
        bad_row = "only\tthree\tcolumns"
        tsv = self._make_tsv([SAMPLE_HEADER, bad_row, SAMPLE_DATA_ROWS[0]])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert len(records) == 1

    def test_parse_empty_ccds_id_skipped(self) -> None:
        row = "chr1\tNC_000001.11\t1\tGENE\t1\t\tPublic\t+\t1\t100\t;\tNA"
        tsv = self._make_tsv([SAMPLE_HEADER, row])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert records == []

    def test_parse_strips_whitespace(self) -> None:
        row = " chr1 \t NC_000001.11 \t 1 \t A1BG \t 1 \t CCDS1.1 \t Public \t - \t 11873 \t 11873 \t ; \t NA "
        tsv = self._make_tsv([SAMPLE_HEADER, row])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert len(records) == 1
        assert records[0].chromosome == "chr1"
        assert records[0].symbol == "A1BG"

    def test_parse_multiple_rows(self) -> None:
        tsv = self._make_tsv([SAMPLE_HEADER] + SAMPLE_DATA_ROWS)
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        ccds_ids = [r.ccds_id for r in records]
        assert ccds_ids == ["CCDS1.1", "CCDS2.2", "CCDS3.1", "CCDS4.1"]

    def test_parse_handles_trailing_tabs(self) -> None:
        row = "chr1\tNC_000001.11\t1\tA1BG\t1\tCCDS1.1\tPublic\t-\t11873\t11873\t;\tNotAvailable\t\t\t"
        tsv = self._make_tsv([SAMPLE_HEADER, row])
        parser = CcdsTsvParser()
        records = parser.parse(io.StringIO(tsv))
        assert len(records) == 1
