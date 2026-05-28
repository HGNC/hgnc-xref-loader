"""Release-aware Ensembl core database resolution.

Provides a concrete EnsemblContextProvider implementation that resolves the
appropriate Ensembl core database name from configuration. The resolved name
is memoized for the lifetime of the job to pin the database for the run.
"""

from __future__ import annotations

from typing import Literal

from hgnc_xref_loader.ensembl_exceptions import EnsemblDbResolutionError
from hgnc_xref_loader.repositories.ensembl_interfaces import EnsemblContextProvider

SPECIES_ALIASES: dict[str, str] = {
    "homo_sapiens": "homo_sapiens",
    "human": "homo_sapiens",
    "hsapiens": "homo_sapiens",
    "mus_musculus": "mus_musculus",
    "mouse": "mus_musculus",
    "mmusculus": "mus_musculus",
}


class EnsemblDbResolver(EnsemblContextProvider):
    """Resolve and pin the Ensembl core database name for a job run.

    Accepts either an explicit database name or resolution parameters
    (host, species, release) to construct the core database name. The result
    is memoized after first resolution.

    Args:
        database: Explicit core database name (e.g. "homo_sapiens_core_110_38").
        host: Ensembl MySQL host (used for documentation/validation).
        species: Species name or alias (e.g. "homo_sapiens", "human").
        release: Ensembl release number.
        assembly: Assembly version suffix (e.g. "38").
    """

    def __init__(
        self,
        database: str | None = None,
        host: str | None = None,
        species: str | None = None,
        release: int | None = None,
        assembly: str | None = None,
    ) -> None:
        self._database = database
        self._host = host
        self._species = species
        self._release = release
        self._assembly = assembly
        self._resolved: str | None = None

    def get_core_db_name(self) -> str:
        """Return the resolved Ensembl core database name.

        If an explicit database name was provided, returns it directly.
        Otherwise, constructs the name from species, release, and assembly.

        Returns:
            The resolved core database name.

        Raises:
            EnsemblDbResolutionError: If resolution fails due to missing
                parameters or unknown species.
        """
        if self._resolved is not None:
            return self._resolved

        if self._database is not None:
            self._resolved = self._database
            return self._resolved

        if self._species is None or self._release is None:
            raise EnsemblDbResolutionError(
                "Cannot resolve core database: no explicit database name "
                "and insufficient resolution parameters (species and release required)."
            )

        resolved_species = SPECIES_ALIASES.get(self._species.lower())
        if resolved_species is None:
            raise EnsemblDbResolutionError(
                f"Cannot resolve core database: unknown species '{self._species}'. "
                f"Known species: {', '.join(sorted(set(SPECIES_ALIASES.values())))}."
            )

        parts = [resolved_species, "core", str(self._release)]
        if self._assembly is not None:
            parts.append(self._assembly)

        self._resolved = "_".join(parts)
        return self._resolved
