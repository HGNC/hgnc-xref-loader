"""Tests for shared TSV/CSV parser.

Validates the configurable tabular parser used by all xref loaders
that download TSV or CSV files.
"""

from __future__ import annotations

import pytest

from hgnc_xref_loader.loaders.tabular_parser import (
    TabularParser,
    TabularParserConfig,
)


class TestTabularParserConfig:
    """Test parser configuration."""

    def test_default_config(self) -> None:
        config = TabularParserConfig()
        assert config.delimiter == "\t"
        assert config.header_lines == 0
        assert config.has_column_header is True

    def test_custom_config(self) -> None:
        config = TabularParserConfig(
            delimiter=",",
            header_lines=18,
            has_column_header=False,
        )
        assert config.delimiter == ","
        assert config.header_lines == 18


class TestTabularParserBasic:
    """Test basic parsing."""

    def test_parse_tsv_with_header(self) -> None:
        config = TabularParserConfig(delimiter="\t", has_column_header=True)
        parser = TabularParser(config)
        data = b"col_a\tcol_b\tcol_c\n1\t2\t3\n4\t5\t6\n"
        rows = parser.parse(data)
        assert len(rows) == 2
        assert rows[0]["col_a"] == "1"
        assert rows[1]["col_c"] == "6"

    def test_parse_csv(self) -> None:
        config = TabularParserConfig(delimiter=",", has_column_header=True)
        parser = TabularParser(config)
        data = b"name,value\nfoo,bar\nbaz,qux\n"
        rows = parser.parse(data)
        assert len(rows) == 2
        assert rows[0]["name"] == "foo"

    def test_parse_with_column_names_override(self) -> None:
        config = TabularParserConfig(
            delimiter="\t",
            has_column_header=False,
            column_names=["a", "b", "c"],
        )
        parser = TabularParser(config)
        data = b"1\t2\t3\n4\t5\t6\n"
        rows = parser.parse(data)
        assert rows[0]["a"] == "1"

    def test_skip_header_lines(self) -> None:
        config = TabularParserConfig(
            delimiter="\t",
            header_lines=2,
            has_column_header=True,
        )
        parser = TabularParser(config)
        data = b"skip1\nskip2\ncol_a\tcol_b\n1\t2\n"
        rows = parser.parse(data)
        assert len(rows) == 1
        assert rows[0]["col_a"] == "1"


class TestTabularParserEdgeCases:
    """Test edge cases."""

    def test_empty_data(self) -> None:
        config = TabularParserConfig()
        parser = TabularParser(config)
        rows = parser.parse(b"")
        assert rows == []

    def test_only_header(self) -> None:
        config = TabularParserConfig(has_column_header=True)
        parser = TabularParser(config)
        rows = parser.parse(b"col_a\tcol_b\n")
        assert rows == []

    def test_short_rows_padded(self) -> None:
        config = TabularParserConfig(
            delimiter="\t",
            has_column_header=False,
            column_names=["a", "b", "c"],
        )
        parser = TabularParser(config)
        data = b"1\t2\n"
        rows = parser.parse(data)
        assert len(rows) == 1
        assert rows[0].get("c") == ""

    def test_gzip_decompression(self) -> None:
        import gzip

        config = TabularParserConfig(
            delimiter="\t",
            has_column_header=True,
            compressed=True,
        )
        parser = TabularParser(config)
        raw = b"col_a\tcol_b\n1\t2\n3\t4\n"
        data = gzip.compress(raw)
        rows = parser.parse(data)
        assert len(rows) == 2
        assert rows[0]["col_a"] == "1"
