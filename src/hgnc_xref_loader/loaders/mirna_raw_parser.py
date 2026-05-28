"""miRNA raw GFF3 parser for miRBase hsa.gff3 data.

Parses the miRBase GFF3 file, filtering for primary_transcript features.

Staging table columns:
    mirn_seqname, mirn_source, mirn_feature, mirn_start, mirn_end,
    mirn_score, mirn_strand, mirn_frame, mirn_attributes
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADER_LINES = 0
TARGET_FEATURE = "primary_transcript"


@dataclass(frozen=True)
class MirnaRawRecord:
    """A single mirna_raw staging row."""

    mirn_seqname: str
    mirn_source: str
    mirn_feature: str
    mirn_start: str
    mirn_end: str
    mirn_score: str
    mirn_strand: str
    mirn_frame: str
    mirn_attributes: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "mirn_seqname": self.mirn_seqname,
            "mirn_source": self.mirn_source,
            "mirn_feature": self.mirn_feature,
            "mirn_start": self.mirn_start,
            "mirn_end": self.mirn_end,
            "mirn_score": self.mirn_score,
            "mirn_strand": self.mirn_strand,
            "mirn_frame": self.mirn_frame,
            "mirn_attributes": self.mirn_attributes,
        }


class MirnaRawParser:
    """Parse miRBase GFF3 into MirnaRawRecord staging rows.

    Filters for primary_transcript features only.
    """

    def parse(self, data: bytes) -> list[MirnaRawRecord]:
        """Parse miRBase GFF3 data.

        Args:
            data: Raw GFF3 bytes from miRBase.

        Returns:
            List of ``MirnaRawRecord`` instances for primary_transcript features.
        """
        text = data.decode("utf-8")
        records: list[MirnaRawRecord] = []

        for line in text.splitlines():
            if line.startswith("#"):
                continue

            cols = line.split("\t")
            if len(cols) < 9:
                continue

            if cols[2].strip() != TARGET_FEATURE:
                continue

            records.append(
                MirnaRawRecord(
                    mirn_seqname=cols[0].strip(),
                    mirn_source=cols[1].strip(),
                    mirn_feature=cols[2].strip(),
                    mirn_start=cols[3].strip(),
                    mirn_end=cols[4].strip(),
                    mirn_score=self._clean(cols[5]),
                    mirn_strand=cols[6].strip(),
                    mirn_frame=self._clean(cols[7]),
                    mirn_attributes=cols[8].strip(),
                )
            )

        logger.info(
            "mirna_raw_parsed",
            extra={"record_count": len(records)},
        )
        return records

    @staticmethod
    def _clean(val: str) -> str:
        """Clean a GFF field value. Replaces '.' with empty string."""
        stripped = val.strip()
        return "" if stripped == "." else stripped
