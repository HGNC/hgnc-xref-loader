"""CCDS xref source adapter.

Parses Consensus Coding Sequence (CCDS) mapping data, linking CCDS IDs
to HGNC gene identifiers.
"""

from __future__ import annotations

from hgnc_xref_loader.domain.models import XrefRecord
from hgnc_xref_loader.fetch.client import XrefFetchClient
from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.registry import register_source
from hgnc_xref_loader.repositories.xref_staging_repository import XrefStagingRepository


@register_source("ccds")
class CcdsXrefLoader(BaseXrefLoader):
    """Load CCDS-to-HGNC cross-reference mappings.

    Parses TSV rows with columns: ccds_id, hgnc_id, symbol, status.

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
            ccds_id = row.get("ccds_id", "").strip()
            symbol = row.get("symbol", "").strip() or None
            status = row.get("status", "").strip() or None
            if not hgnc_id or not ccds_id:
                continue
            records.append(
                XrefRecord(
                    hgnc_id=hgnc_id,
                    external_id=ccds_id,
                    source="ccds",
                    symbol=symbol,
                    status=status,
                )
            )
        return records
