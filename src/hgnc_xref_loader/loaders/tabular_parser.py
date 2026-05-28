"""Configurable tabular parser for TSV/CSV xref data sources.

Handles delimiter configuration, header line skipping, optional
gzip decompression, and column name mapping. Used by all file-based
xref loaders.
"""

from __future__ import annotations

import csv
import gzip
import io
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TabularParserConfig:
    """Configuration for a tabular data parser.

    Attributes:
        delimiter: Field delimiter character.
        header_lines: Number of comment/header lines to skip before the
            column header or data.
        has_column_header: Whether the first non-skipped line is a column
            header.
        column_names: Explicit column names (used when
            ``has_column_header`` is False).
        compressed: Whether the input data is gzip-compressed.
        quoting: CSV quoting mode.
    """

    delimiter: str = "\t"
    header_lines: int = 0
    has_column_header: bool = True
    column_names: list[str] = field(default_factory=list)
    compressed: bool = False
    quoting: int = csv.QUOTE_MINIMAL


class TabularParser:
    """Parse raw bytes of tabular data into a list of row dicts.

    Handles decompression, header skipping, and column name resolution.

    Args:
        config: Parser configuration.
    """

    def __init__(self, config: TabularParserConfig) -> None:
        self._config = config

    def parse(self, data: bytes) -> list[dict[str, str]]:
        """Parse raw bytes into row dicts.

        Args:
            data: Raw file bytes, optionally gzip-compressed.

        Returns:
            List of dicts mapping column names to string values.
        """
        if not data:
            return []

        text = self._decompress(data) if self._config.compressed else data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= self._config.header_lines:
            return []

        data_lines = lines[self._config.header_lines :]

        if not data_lines:
            return []

        if self._config.has_column_header:
            header = data_lines[0].split(self._config.delimiter)
            data_lines = data_lines[1:]
        elif self._config.column_names:
            header = self._config.column_names
        else:
            header = [str(i) for i in range(len(data_lines[0].split(self._config.delimiter)))]

        rows: list[dict[str, str]] = []
        reader = csv.reader(data_lines, delimiter=self._config.delimiter)
        for values in reader:
            row: dict[str, str] = {}
            for i, col_name in enumerate(header):
                row[col_name] = values[i] if i < len(values) else ""
            rows.append(row)

        logger.info(
            "tabular_parse_complete",
            extra={"rows": len(rows), "columns": len(header)},
        )
        return rows

    def _decompress(self, data: bytes) -> str:
        """Decompress gzip data.

        Args:
            data: Gzip-compressed bytes.

        Returns:
            Decompressed string.
        """
        return gzip.decompress(data).decode("utf-8")
