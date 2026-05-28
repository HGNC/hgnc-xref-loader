"""Abstract interfaces for Ensembl repository and context provider abstractions.

Defines ABCs that services depend on for Ensembl data access and database
resolution. Concrete implementations live in the repository layer and use
ensembl-orm under the hood.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hgnc_xref_loader.ensembl_models import Xref
from hgnc_xref_loader.repositories.base_repository import Repository


class EnsemblContextProvider(ABC):
    """Provide resolved Ensembl database context for a job run.

    Implementations encapsulate logic for resolving the appropriate Ensembl
    core database name based on configuration such as release, species, and host.
    The resolved name is memoized for the lifetime of the job.
    """

    @abstractmethod
    def get_core_db_name(self) -> str:
        """Return the resolved Ensembl core database name.

        Returns:
            The resolved core database name (e.g. "homo_sapiens_core_110_38").

        Raises:
            EnsemblDbResolutionError: If resolution fails.
        """


class EnsemblXrefRepository(Repository):
    """Repository for Ensembl cross-reference queries.

    Abstract base for repository implementations that fetch cross-reference
    data from Ensembl using ensembl-orm models.
    """

    @abstractmethod
    def fetch_gene_xrefs(self, gene_stable_id: str) -> list[Xref]:
        """Fetch cross-references for a gene.

        Args:
            gene_stable_id: The Ensembl stable ID of the gene (e.g. "ENSG00000012048").

        Returns:
            List of cross-reference objects.

        Raises:
            EnsemblOrmMissingModelError: If required models are unavailable.
        """
