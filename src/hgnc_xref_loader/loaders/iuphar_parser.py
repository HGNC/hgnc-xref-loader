"""IUPHAR CSV parser for the Guide to Pharmacology HGNC mapping.

Parses CSV data from the IUPHAR/GtoP HGNC mapping file.

Staging table columns:
    iu_app_sym, iu_hgnc_id, iu_receptor_name, iu_id, iu_receptor_id
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1
OBJECT_ID_RE = re.compile(r"\?(objectId|ligandId)=(\d+)")


@dataclass(frozen=True)
class IupharRecord:
    """A single IUPHAR staging row.

    Attributes:
        iu_app_sym: Approved gene symbol.
        iu_hgnc_id: HGNC numeric ID.
        iu_receptor_name: Receptor/target name.
        iu_id: Constructed IUPHAR ID string (objectId=N or ligandId=N).
        iu_receptor_id: Receptor ID from URL.
    """

    iu_app_sym: str
    iu_hgnc_id: int
    iu_receptor_name: str
    iu_id: str
    iu_receptor_id: str

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "iu_app_sym": self.iu_app_sym,
            "iu_hgnc_id": self.iu_hgnc_id,
            "iu_receptor_name": self.iu_receptor_name,
            "iu_id": self.iu_id,
            "iu_receptor_id": self.iu_receptor_id,
        }


class IupharParser:
    """Parse IUPHAR CSV into IupharRecord staging rows."""

    def parse(self, data: bytes) -> list[IupharRecord]:
        """Parse CSV data from IUPHAR.

        Args:
            data: Raw CSV bytes.

        Returns:
            List of ``IupharRecord`` instances.
        """
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[IupharRecord] = []
        reader = csv.reader(lines[HEADER_LINES:])

        for cols in reader:
            if len(cols) < 6:
                continue

            try:
                hgnc_id = int(cols[1].strip())
            except (ValueError, IndexError):
                continue

            iu_id = self._construct_id(cols)
            receptor_id = cols[5].strip() if len(cols) > 5 else ""

            records.append(
                IupharRecord(
                    iu_app_sym=cols[0].strip(),
                    iu_hgnc_id=hgnc_id,
                    iu_receptor_name=cols[2].strip(),
                    iu_id=iu_id,
                    iu_receptor_id=receptor_id,
                )
            )

        logger.info(
            "iuphar_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _construct_id(cols: list[str]) -> str:
        """Construct the IUPHAR ID from URL columns.

        Args:
            cols: CSV column values.

        Returns:
            Constructed ID string like 'objectId=123' or 'ligandId=456'.
        """
        url_col = cols[4] if len(cols) > 4 else ""
        match = OBJECT_ID_RE.search(url_col)
        if match:
            return f"{match.group(1)}={match.group(2)}"

        id_match = re.search(r'"(\d+)"', cols[3]) if len(cols) > 3 else None
        if id_match:
            prefix_match = OBJECT_ID_RE.search(url_col)
            prefix = prefix_match.group(1) if prefix_match else "objectId"
            return f"{prefix}={id_match.group(1)}"

        return ""
