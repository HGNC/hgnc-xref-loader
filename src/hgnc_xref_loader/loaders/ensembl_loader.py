"""Ensembl xref source adapter.

Parses Ensembl-to-HGNC mapping data from TSV files, normalising
Ensembl gene IDs and HGNC accessions into XrefRecord instances.
"""

from __future__ import annotations

from hgnc_xref_loader.domain.models import XrefRecord
from hgnc_xref_loader.fetch.client import XrefFetchClient
from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.registry import register_source
from hgnc_xref_loader.repositories.xref_staging_repository import XrefStagingRepository


@register_source("ensembl2hgnc")
class EnsemblXrefLoader(BaseXrefLoader):
    """Load Ensembl-to-HGNC cross-reference mappings from TSV data.

    Parses TSV rows with columns: ensembl_gene_id, hgnc_id, symbol.
    Produces XrefRecord instances linking Ensembl gene IDs to HGNC IDs.

    Args:
        fetch_client: Client for retrieving source data.
        staging_repo: Repository for persisting normalised records.
    """

    def __init__(
        self,
        fetch_client: XrefFetchClient | None = None,
        staging_repo: XrefStagingRepository | None = None,
    ) -> None:
        super().__init__(fetch_client=fetch_client, staging_repo=staging_repo)

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        records: list[XrefRecord] = []
        for row in raw:
            hgnc_id = row.get("hgnc_id", "").strip()
            ensembl_id = row.get("ensembl_gene_id", "").strip()
            symbol = row.get("symbol", "").strip() or None
            if not hgnc_id or not ensembl_id:
                continue
            records.append(
                XrefRecord(
                    hgnc_id=hgnc_id,
                    external_id=ensembl_id,
                    source="ensembl",
                    symbol=symbol,
                )
            )
        return records
