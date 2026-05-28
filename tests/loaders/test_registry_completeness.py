"""Tests verifying all XrefSource values are registered.

Validates that every XrefSource enum member has a corresponding
registered loader class in the registry.
"""

from __future__ import annotations

import pytest

from hgnc_xref_loader.loaders import registry as reg


class TestRegistryCompleteness:
    """Verify all XrefSource values have registered loaders."""

    def test_all_sources_registered(self) -> None:
        import hgnc_xref_loader.loaders.individual_loaders
        import hgnc_xref_loader.loaders.uniprot_loader
        import hgnc_xref_loader.loaders.ccds_loader
        import hgnc_xref_loader.loaders.ensembl_loader

        for source in reg.XrefSource:
            loader_cls = reg.get_loader(source)
            assert loader_cls is not None, f"No loader registered for {source.value}"

    def test_xref_source_count(self) -> None:
        assert len(reg.XrefSource) == 27

    def test_specific_loaders_not_scaffolds(self) -> None:
        import hgnc_xref_loader.loaders.uniprot_loader
        import hgnc_xref_loader.loaders.ccds_loader
        import hgnc_xref_loader.loaders.ensembl_loader

        uniprot_cls = reg.get_loader(reg.XrefSource.UNIPROT)
        ccds_cls = reg.get_loader(reg.XrefSource.CCDS)
        ensembl_cls = reg.get_loader(reg.XrefSource.ENSEMBL2HGNC)

        assert "UniprotXrefLoader" in uniprot_cls.__name__
        assert "CcdsXrefLoader" in ccds_cls.__name__
        assert "EnsemblXrefLoader" in ensembl_cls.__name__
