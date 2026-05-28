"""Scaffolded xref source adapters for remaining 24 sources.

Each adapter raises NotImplementedError with a TODO message referencing
the specific source and AGENTS guidance. These stubs allow the registry
to reference a complete set of 27 sources while individual adapters
are implemented incrementally.
"""

from __future__ import annotations

from hgnc_xref_loader.domain.models import XrefRecord
from hgnc_xref_loader.fetch.client import XrefFetchClient
from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.registry import register_source
from hgnc_xref_loader.repositories.xref_staging_repository import XrefStagingRepository


def _make_scaffold(source_name: str):
    @register_source(source_name)
    class ScaffoldLoader(BaseXrefLoader):
        def __init__(
            self,
            fetch_client: XrefFetchClient | None = None,
            staging_repo: XrefStagingRepository | None = None,
        ) -> None:
            super().__init__(fetch_client=fetch_client, staging_repo=staging_repo)

        def fetch_and_parse(self) -> list[dict]:
            raise NotImplementedError(
                f"TODO: Implement fetch_and_parse for xref source '{source_name}'. "
                "See AGENTS.md for parsing/normalization guidance."
            )

        def normalize(self, raw: list[dict]) -> list[XrefRecord]:
            raise NotImplementedError(
                f"TODO: Implement normalize for xref source '{source_name}'. "
                "See AGENTS.md for parsing/normalization guidance."
            )

    ScaffoldLoader.__name__ = f"{source_name.replace('_', ' ').title().replace(' ', '')}Loader"
    ScaffoldLoader.__qualname__ = ScaffoldLoader.__name__
    return ScaffoldLoader


ScaffoldLoaders = {
    name: _make_scaffold(name)
    for name in [
        "gencc", "mane", "gene_info", "gene_history", "gene2accession",
        "gene2refseq", "iuphar", "mirna_raw", "omim2gene", "cytoband",
        "lovd", "ncbi2namelist", "rgd_orthologs", "ucsc2hgnc",
        "ensembl2hgnc_complete", "ensembl_seq", "imgt", "refseq_catalog",
        "rna_central", "ccds_seq", "mgi", "ensembl_gene", "agr", "alphafold",
    ]
}
