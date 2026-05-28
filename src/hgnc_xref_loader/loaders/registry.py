"""Loader registry mapping XrefSource values to loader implementations.

Provides the XrefSource enum with all 27 allowed cross-reference source
names, plus register_source() and get_loader() for loader discovery.
"""

from __future__ import annotations

import enum
from typing import Type

from hgnc_xref_loader.loaders.base import BaseXrefLoader

_LOADERS: dict[XrefSource, type[BaseXrefLoader]] = {}


class XrefSource(str, enum.Enum):
    """Enumeration of all 27 supported cross-reference source identifiers.

    Each member corresponds to an XREF_SOURCE value that can be configured
    via environment variable and mapped to a concrete loader implementation.
    """

    GENCC = "gencc"
    MANE = "mane"
    GENE_INFO = "gene_info"
    GENE_HISTORY = "gene_history"
    GENE2ACCESSION = "gene2accession"
    GENE2REFSEQ = "gene2refseq"
    IUPHAR = "iuphar"
    MIRNA_RAW = "mirna_raw"
    OMIM2GENE = "omim2gene"
    CYTOBAND = "cytoband"
    LOVD = "lovd"
    NCBI2NAMELIST = "ncbi2namelist"
    RGD_ORTHOLOGS = "rgd_orthologs"
    UCSC2HGNC = "ucsc2hgnc"
    ENSEMBL2HGNC = "ensembl2hgnc"
    ENSEMBL_SEQ = "ensembl_seq"
    IMGT = "imgt"
    REFSEQ_CATALOG = "refseq_catalog"
    RNA_CENTRAL = "rna_central"
    CCDS_SEQ = "ccds_seq"
    CCDS = "ccds"
    MGI = "mgi"
    UNIPROT = "uniprot"
    ENSEMBL2HGNC_COMPLETE = "ensembl2hgnc_complete"
    ENSEMBL_GENE = "ensembl_gene"
    AGR = "agr"
    ALPHAFOLD = "alphafold"


def register_source(source: XrefSource):
    """Return a decorator that registers a loader class for the given source.

    Args:
        source: The XrefSource enum value to associate with the loader.

    Returns:
        A decorator that registers and returns the loader class unchanged.
    """

    def decorator(cls: type[BaseXrefLoader]) -> type[BaseXrefLoader]:
        _LOADERS[source] = cls
        return cls

    return decorator


def get_loader(source: XrefSource) -> type[BaseXrefLoader]:
    """Return the registered loader class for the given source.

    Args:
        source: The XrefSource enum value to look up.

    Returns:
        The loader class registered for the source.

    Raises:
        UnknownSourceError: If no loader has been registered for the source.
    """
    from hgnc_xref_loader.loaders.exceptions import UnknownSourceError

    if source not in _LOADERS:
        raise UnknownSourceError(
            f"No loader registered for source: {source.value!r}"
        )
    return _LOADERS[source]
