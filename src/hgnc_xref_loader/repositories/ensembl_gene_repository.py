"""Ensembl gene MySQL fetch repository.

Queries the Ensembl MySQL database for gene information with HGNC links.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


class EnsemblGeneRepository:
    """Fetch Ensembl gene data from Ensembl MySQL.

    Args:
        ensembl_session_factory: Callable returning an Ensembl SQLAlchemy session.
    """

    def __init__(self, ensembl_session_factory: Any) -> None:
        self._session_factory = ensembl_session_factory

    def fetch_genes(self) -> list[dict[str, Any]]:
        """Fetch all current Ensembl genes with display names and HGNC links.

        Returns:
            List of dicts with name, name_source, gene_id, biotype,
            chromosome, hgnc_id, on_alt_loci fields.
        """
        query = text("""
            SELECT main_xref.display_label AS name,
                   external_db.db_display_name AS name_source,
                   gene.stable_id AS gene_id,
                   gene.biotype,
                   seq_region.name AS chromosome,
                   SUBSTRING(hgnc_link.dbprimary_acc, 6) AS hgnc_id,
                   CASE WHEN sra.attrib_type_id = 16
                        THEN 1 ELSE 0
                   END AS on_alt_loci
            FROM gene
            LEFT OUTER JOIN (
                xref AS main_xref
                JOIN external_db
                    ON main_xref.external_db_id = external_db.external_db_id
            ) ON gene.display_xref_id = main_xref.xref_id
            JOIN seq_region ON gene.seq_region_id = seq_region.seq_region_id
            LEFT OUTER JOIN (
                SELECT object_xref.ensembl_id, xref.dbprimary_acc
                FROM object_xref
                JOIN xref ON object_xref.xref_id = xref.xref_id
                WHERE xref.external_db_id = 1100
            ) AS hgnc_link ON gene.gene_id = hgnc_link.ensembl_id
            LEFT JOIN seq_region_attrib sra
                ON (seq_region.seq_region_id = sra.seq_region_id
                    AND sra.attrib_type_id = 16)
            WHERE gene.is_current = 1
              AND seq_region.coord_system_id = 4
        """)

        rows: list[dict[str, Any]] = []
        with self._session_factory() as session:
            result = session.execute(query)
            for row in result:
                name_source = row[1] or ""
                name_source = name_source.replace(" (formerly Entrezgene)", "")

                hgnc_id = int(row[5]) if row[5] else 0

                rows.append({
                    "name": row[0] or "",
                    "name_source": name_source,
                    "gene_id": row[2] or "",
                    "biotype": row[3] or "",
                    "chromosome": row[4] or "",
                    "hgnc_id": hgnc_id,
                    "on_alt_loci": bool(row[6]),
                })

        logger.info(
            "ensembl_gene_fetched",
            extra={"row_count": len(rows)},
        )
        return rows
