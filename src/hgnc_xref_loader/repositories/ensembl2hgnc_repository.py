"""Ensembl2Hgnc repository for fetching Ensembl-to-HGNC mappings from MySQL.

Queries the Ensembl database via ensembl-orm using SQLAlchemy 2.0 select()
API. Joins Xref, ObjectXref, Gene, SeqRegion, and SeqRegionAttrib to
extract HGNC ID / symbol / Ensembl gene ID triples, filtered to exclude
patch regions and LRG-prefixed identifiers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ensembl_orm.enums import EnsemblObjectType
from ensembl_orm.models import Gene, ObjectXref, SeqRegion, SeqRegionAttrib, Xref
from sqlalchemy import select

logger = logging.getLogger(__name__)

ENSEMBL2HGNC_STAGING_TABLE = "ensembl2hgnc_update"
ENSEMBL2HGNC_STAGING_COLUMNS = [
    "e2h_hgnc_id",
    "e2h_app_sym",
    "e2h_ensembl_gene_id",
]

EXTERNAL_DB_ID_HGNC = 1100
PATCH_ATTRIB_TYPE_ID = 16


@dataclass(frozen=True)
class Ensembl2HgncRecord:
    """A single Ensembl-to-HGNC mapping row.

    Attributes:
        hgnc_id: HGNC accession (e.g. ``HGNC:9052``).
        hgnc_symbol: HGNC gene symbol (e.g. ``PLAU``).
        ensembl_gene_id: Ensembl stable gene ID (e.g. ``ENSG00000124383``).
    """

    hgnc_id: str
    hgnc_symbol: str
    ensembl_gene_id: str

    def to_staging_dict(self) -> dict[str, str]:
        return {
            "e2h_hgnc_id": self.hgnc_id,
            "e2h_app_sym": self.hgnc_symbol,
            "e2h_ensembl_gene_id": self.ensembl_gene_id,
        }


class Ensembl2HgncRepository:
    """Repository for fetching Ensembl-to-HGNC mappings from Ensembl MySQL.

    Uses ensembl-orm models and SQLAlchemy 2.0 ``select()`` to join
    ``xref``, ``object_xref``, ``gene``, ``seq_region``, and
    ``seq_region_attrib`` (patch exclusion via LEFT JOIN).

    Args:
        session: SQLAlchemy Session connected to the Ensembl database.
    """

    def __init__(self, session: Any) -> None:
        self._session = session

    def fetch_mappings(self) -> list[Ensembl2HgncRecord]:
        """Fetch Ensembl-to-HGNC mappings with patch and LRG exclusion.

        Returns:
            List of ``Ensembl2HgncRecord`` instances.

        Raises:
            Exception: Re-raised from database query failures.
        """
        stmt = (
            select(
                Xref.dbprimary_acc.label("hgnc_id"),
                Xref.display_label.label("hgnc_symbol"),
                Gene.stable_id.label("ensembl_gene_id"),
            )
            .join(ObjectXref, ObjectXref.xref_id == Xref.xref_id)
            .join(Gene, ObjectXref.ensembl_id == Gene.gene_id)
            .join(SeqRegion, Gene.seq_region_id == SeqRegion.seq_region_id)
            .outerjoin(
                SeqRegionAttrib,
                (SeqRegion.seq_region_id == SeqRegionAttrib.seq_region_id)
                & (SeqRegionAttrib.attrib_type_id == PATCH_ATTRIB_TYPE_ID),
            )
            .where(
                ObjectXref.ensembl_object_type == EnsemblObjectType.GENE,
                Xref.external_db_id == EXTERNAL_DB_ID_HGNC,
                SeqRegionAttrib.seq_region_id.is_(None),
            )
        )

        results = self._session.execute(stmt)
        records: list[Ensembl2HgncRecord] = []

        for row in results:
            hgnc_id = row[0] or ""
            hgnc_symbol = row[1] or ""
            ensembl_gene_id = row[2] or ""

            if ensembl_gene_id.startswith("LRG"):
                continue

            records.append(
                Ensembl2HgncRecord(
                    hgnc_id=hgnc_id,
                    hgnc_symbol=hgnc_symbol,
                    ensembl_gene_id=ensembl_gene_id,
                )
            )

        logger.info(
            "ensembl2hgnc_fetched",
            extra={"record_count": len(records)},
        )
        return records
