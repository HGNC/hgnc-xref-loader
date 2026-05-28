"""Individual xref source adapters replacing scaffold stubs.

Each adapter is a thin ``BaseXrefLoader`` subclass registered with the
loader registry. The ``run()`` method delegates to the corresponding
concrete service class which handles the full fetch/parse/stage/promote
lifecycle.

The ``fetch_and_parse()`` and ``normalize()`` methods from the base class
template are not used — ``run()`` is overridden entirely.
"""

from __future__ import annotations

from hgnc_xref_loader.domain.models import XrefRecord
from hgnc_xref_loader.fetch.client import XrefFetchClient
from hgnc_xref_loader.loaders.base import BaseXrefLoader
from hgnc_xref_loader.loaders.registry import register_source, XrefSource
from hgnc_xref_loader.repositories.xref_staging_repository import (
    XrefStagingRepository,
)


@register_source(XrefSource.GENE_INFO)
class GeneInfoLoader(BaseXrefLoader):
    """Load NCBI gene_info cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.GENE_HISTORY)
class GeneHistoryLoader(BaseXrefLoader):
    """Load NCBI gene_history cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.GENE2ACCESSION)
class Gene2AccessionLoader(BaseXrefLoader):
    """Load NCBI gene2accession cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.GENE2REFSEQ)
class Gene2RefseqLoader(BaseXrefLoader):
    """Load NCBI gene2refseq cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.REFSEQ_CATALOG)
class RefseqCatalogLoader(BaseXrefLoader):
    """Load NCBI RefSeq catalog cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.RNA_CENTRAL)
class RnaCentralLoader(BaseXrefLoader):
    """Load RNAcentral cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.NCBI2NAMELIST)
class Ncbi2NamelistLoader(BaseXrefLoader):
    """Load NCBI to_name cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.CCDS_SEQ)
class CcdsSeqLoader(BaseXrefLoader):
    """Load CCDS sequence cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.GENCC)
class GenCCLoader(BaseXrefLoader):
    """Load GenCC cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.IUPHAR)
class IupharLoader(BaseXrefLoader):
    """Load IUPHAR/GtoP cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.MANE)
class ManeLoader(BaseXrefLoader):
    """Load NCBI MANE cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.OMIM2GENE)
class Omim2GeneLoader(BaseXrefLoader):
    """Load OMIM mim2gene cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.RGD_ORTHOLOGS)
class RgdOrthologsLoader(BaseXrefLoader):
    """Load RGD orthologs cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.AGR)
class AgrLoader(BaseXrefLoader):
    """Load Alliance genome cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.MGI)
class MgiLoader(BaseXrefLoader):
    """Load MGI homology cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.ENSEMBL2HGNC_COMPLETE)
class Ensembl2HgncCompleteLoader(BaseXrefLoader):
    """Load complete Ensembl-to-HGNC cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.ENSEMBL_GENE)
class EnsemblGeneLoader(BaseXrefLoader):
    """Load Ensembl gene cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.ENSEMBL_SEQ)
class EnsemblSeqLoader(BaseXrefLoader):
    """Load Ensembl sequence cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.MIRNA_RAW)
class MirnaRawLoader(BaseXrefLoader):
    """Load miRBase miRNA cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.ALPHAFOLD)
class AlphafoldLoader(BaseXrefLoader):
    """Load Alphafold cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.CYTOBAND)
class CytobandLoader(BaseXrefLoader):
    """Load cytoband cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.LOVD)
class LovdLoader(BaseXrefLoader):
    """Load LOVD cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.UCSC2HGNC)
class Ucsc2HgncLoader(BaseXrefLoader):
    """Load UCSC-to-HGNC cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []


@register_source(XrefSource.IMGT)
class ImgtLoader(BaseXrefLoader):
    """Load IMGT/GENE-DB cross-reference data."""

    def fetch_and_parse(self) -> list[dict]:
        return []

    def normalize(self, raw: list[dict]) -> list[XrefRecord]:
        return []
