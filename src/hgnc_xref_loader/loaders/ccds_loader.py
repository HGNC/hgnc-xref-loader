"""CCDS xref source adapter.

Parses Consensus Coding Sequence (CCDS) mapping data, linking CCDS IDs
to HGNC gene identifiers. Supports an optional post-load hook for
executing CCDS-specific gene column mutations after the standard lifecycle.
"""

from __future__ import annotations

from typing import Callable

from hgnc_xref_loader.domain.models import XrefRecord
from hgnc_xref_loader.fetch.client import XrefFetchClient
from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.registry import register_source
from hgnc_xref_loader.repositories.xref_staging_repository import XrefStagingRepository


@register_source("ccds")
class CcdsXrefLoader(BaseXrefLoader):
    """Load CCDS-to-HGNC cross-reference mappings.

    Parses TSV rows with columns: ccds_id, hgnc_id, symbol, status.
    Optionally invokes a post-load hook after the standard lifecycle
    for CCDS-specific gene column mutations (add_hgnc_ids, etc.).

    Args:
        fetch_client: Client for retrieving source data.
        staging_repo: Repository for persisting normalised records.
        post_load_hook: Optional callable invoked after the standard
            fetch-normalize lifecycle completes successfully.
    """

    def __init__(
        self,
        fetch_client: XrefFetchClient | None = None,
        staging_repo: XrefStagingRepository | None = None,
        post_load_hook: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(fetch_client=fetch_client, staging_repo=staging_repo)
        self._post_load_hook = post_load_hook

    def run(self) -> int:
        """Execute the loader lifecycle then invoke the post-load hook.

        Returns:
            The number of normalised records produced.
        """
        count = super().run()
        if self._post_load_hook is not None:
            self._post_load_hook()
        return count

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
