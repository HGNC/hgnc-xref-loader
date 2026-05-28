"""Alphafold CSV parser for EBI accession_ids.csv data.

Parses the Alphafold accession ID mapping CSV file.

Staging table columns:
    swissprot_acc, alphafold_acc, version
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 10


@dataclass(frozen=True)
class AlphafoldRecord:
    """A single alphafold staging row."""

    swissprot_acc: str
    alphafold_acc: str
    version: int

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "swissprot_acc": self.swissprot_acc,
            "alphafold_acc": self.alphafold_acc,
            "version": self.version,
        }


class AlphafoldParser:
    """Parse Alphafold accession CSV into AlphafoldRecord rows."""

    def parse(self, data: bytes) -> list[AlphafoldRecord]:
        """Parse Alphafold accession_ids.csv data.

        Args:
            data: Raw CSV bytes from EBI FTP.

        Returns:
            List of ``AlphafoldRecord`` instances.
        """
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[AlphafoldRecord] = []
        reader = csv.reader(lines[HEADER_LINES:])

        for cols in reader:
            if len(cols) < 5:
                continue

            try:
                version = int(cols[4].strip())
            except ValueError:
                continue

            records.append(
                AlphafoldRecord(
                    swissprot_acc=cols[0].strip(),
                    alphafold_acc=cols[3].strip(),
                    version=version,
                )
            )

        logger.info(
            "alphafold_parsed",
            extra={"record_count": len(records)},
        )
        return records
