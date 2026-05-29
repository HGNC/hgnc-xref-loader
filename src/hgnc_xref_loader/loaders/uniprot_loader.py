"""UniProt xref source adapter.

Parses UniProt-to-HGNC mapping data, linking UniProt accession numbers
to HGNC gene identifiers.
"""

from __future__ import annotations

from hgnc_xref_loader.domain.models import XrefRecord
from hgnc_xref_loader.fetch.client import DefaultXrefFetchClient, XrefFetchClient
from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.registry import register_source
from hgnc_xref_loader.repositories.xref_staging_repository import XrefStagingRepository


@register_source("uniprot")
class UniprotXrefLoader(BaseXrefLoader):
    """Load UniProt-to-HGNC cross-reference mappings.

    Parses TSV rows with columns: uniprot_id, hgnc_id, symbol, status.

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
        self._url = (
            "https://rest.uniprot.org/uniprotkb/stream"
            "?fields=accession,reviewed,entry_name,protein_names,gene_primary,"
            "xref_hgnc,ec,xref_geneid"
            "&format=tsv&query=(organism_id:9606)"
        )

    def fetch_and_parse(self) -> list[dict]:
        from hgnc_xref_loader.loaders.uniprot_parser import UniprotTsvParser

        client = self._fetch_client or DefaultXrefFetchClient()
        data = client.fetch(self._url)
        parsed = UniprotTsvParser().parse(data)
        return [row.to_dict() for row in parsed.main_rows]

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        records: list[XrefRecord] = []
        for row in raw:
            hgnc_id = row.get("hgnc_id", "").strip()
            uniprot_id = row.get("uniprot_id", "").strip()
            symbol = row.get("symbol", "").strip() or None
            status = row.get("status", "").strip() or None
            if not hgnc_id or not uniprot_id:
                continue
            records.append(
                XrefRecord(
                    hgnc_id=hgnc_id,
                    external_id=uniprot_id,
                    source="uniprot",
                    symbol=symbol,
                    status=status,
                )
            )
        return records
