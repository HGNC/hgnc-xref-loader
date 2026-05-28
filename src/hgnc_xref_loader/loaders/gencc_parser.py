"""GenCC CSV parser for the GenCC submissions export.

Parses CSV data from the GenCC submissions export API, extracting HGNC
numeric ID and OMIM ID from prefixed identifiers.

Staging table columns:
    uuid, hgnc_id, disease_id, disease_title, omim_id
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 1
HGNC_RE = re.compile(r"HGNC:(\d+)")
OMIM_RE = re.compile(r"OMIM:(\d+)")


@dataclass(frozen=True)
class GenCCRecord:
    """A single gencc staging row.

    Attributes:
        uuid: Submission UUID.
        hgnc_id: HGNC numeric ID.
        disease_id: Disease identifier.
        disease_title: Disease title text.
        omim_id: OMIM numeric ID (0 if absent).
    """

    uuid: str
    hgnc_id: int
    disease_id: str
    disease_title: str
    omim_id: int

    def to_staging_dict(self) -> dict[str, str | int]:
        return {
            "uuid": self.uuid,
            "hgnc_id": self.hgnc_id,
            "disease_id": self.disease_id,
            "disease_title": self.disease_title,
            "omim_id": self.omim_id,
        }


class GenCCParser:
    """Parse GenCC CSV export into GenCCRecord staging rows.

    Extracts HGNC and OMIM numeric IDs from prefixed identifiers.
    Only includes rows with a valid HGNC ID.
    """

    def parse(self, data: bytes) -> list[GenCCRecord]:
        """Parse CSV data from the GenCC export.

        Args:
            data: Raw CSV bytes from GenCC.

        Returns:
            List of ``GenCCRecord`` instances with valid HGNC IDs.
        """
        text = data.decode("utf-8")
        lines = text.splitlines()

        if len(lines) <= HEADER_LINES:
            return []

        records: list[GenCCRecord] = []
        reader = csv.reader(lines[HEADER_LINES:])

        for cols in reader:
            if len(cols) < 6:
                continue

            hgnc_match = HGNC_RE.search(cols[1])
            if not hgnc_match:
                continue

            hgnc_id = int(hgnc_match.group(1))

            omim_match = OMIM_RE.search(cols[5])
            omim_id = int(omim_match.group(1)) if omim_match else 0

            records.append(
                GenCCRecord(
                    uuid=cols[0].strip(),
                    hgnc_id=hgnc_id,
                    disease_id=cols[3].strip(),
                    disease_title=cols[4].strip(),
                    omim_id=omim_id,
                )
            )

        logger.info(
            "gencc_parsed",
            extra={"record_count": len(records)},
        )
        return records
