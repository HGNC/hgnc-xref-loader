"""Ensembl2Hgnc complete MySQL fetch repository.

Queries the Ensembl MySQL database for ALL Ensembl gene-to-HGNC mappings,
including alt-loci regions, using ensembl-orm.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


class Ensembl2HgncCompleteRepository:
    """Fetch Ensembl-to-HGNC complete mappings from Ensembl MySQL.

    Queries the Ensembl homo_sapiens_core database for all xref mappings
    where external_db_id=1100 (HGNC), including alt-loci genes.

    Args:
        ensembl_session_factory: Callable returning an Ensembl SQLAlchemy session.
    """

    def __init__(self, ensembl_session_factory: Any) -> None:
        self._session_factory = ensembl_session_factory

    def fetch_all_mappings(self) -> list[dict[str, Any]]:
        """Fetch all Ensembl-to-HGNC gene mappings.

        Returns:
            List of dicts with hgnc_id, app_sym, ensembl_gene_id,
            biotype, and mapped (Reference/Alt-loci) fields.
        """
        query = text("""
            SELECT SUBSTRING(x.dbprimary_acc, 6) AS hgnc_id,
                   x.display_label AS app_sym,
                   g.stable_id AS ensembl_gene_id,
                   g.biotype,
                   CASE WHEN sra.attrib_type_id = 16
                        THEN 'Alt-loci' ELSE 'Reference'
                   END AS mapped
            FROM xref x
            JOIN object_xref ox             ON (x.xref_id = ox.xref_id)
            JOIN gene g                     ON (ox.ensembl_id = g.gene_id)
            JOIN seq_region sr              ON (g.seq_region_id = sr.seq_region_id)
            LEFT JOIN seq_region_attrib sra ON (sr.seq_region_id = sra.seq_region_id
                                                AND sra.attrib_type_id = 16)
            WHERE ox.ensembl_object_type = 'Gene'
              AND x.external_db_id = 1100
              AND g.stable_id LIKE 'ENSG%'
            ORDER BY app_sym ASC, mapped DESC, ensembl_gene_id ASC
        """)

        rows: list[dict[str, Any]] = []
        with self._session_factory() as session:
            result = session.execute(query)
            for row in result:
                rows.append({
                    "e2ha_hgnc_id": int(row[0]) if row[0] else 0,
                    "e2ha_app_sym": row[1] or "",
                    "e2ha_ensembl_gene_id": row[2] or "",
                    "e2ha_biotype": row[3] or "",
                    "e2ha_mapped": row[4] or "Reference",
                })

        logger.info(
            "ensembl2hgnc_complete_fetched",
            extra={"row_count": len(rows)},
        )
        return rows
