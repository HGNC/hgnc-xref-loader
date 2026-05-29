"""Tests for XrefLoadService CCDS post-load wiring.

Validates that when source is CCDS and a CcdsPostLoadService is provided,
the service wires add_hgnc_ids as a post-load hook on the CcdsXrefLoader.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.loaders.registry import XrefSource
from hgnc_xref_loader.services.xref_load_service import XrefLoadService


class TestXrefLoadServiceCcdsWiring:
    """Tests for CCDS post-load hook wiring in XrefLoadService."""

    def test_ccds_source_passes_post_load_hook(self) -> None:
        mock_post_load = MagicMock()
        logger = MagicMock()

        service = XrefLoadService(
            source=XrefSource.CCDS,
            logger=logger,
            ccds_post_load_service=mock_post_load,
        )

        with patch(
            "hgnc_xref_loader.services.xref_load_service.get_loader"
        ) as mock_get_loader:
            mock_loader_cls = MagicMock()
            mock_loader_instance = MagicMock()
            mock_loader_instance.run.return_value = 0
            mock_loader_cls.return_value = mock_loader_instance
            mock_get_loader.return_value = mock_loader_cls

            service.run()

            mock_loader_cls.assert_called_once()
            call_kwargs = mock_loader_cls.call_args.kwargs
            assert "post_load_hook" in call_kwargs
            assert call_kwargs["post_load_hook"] == mock_post_load.add_hgnc_ids

    def test_non_ccds_source_does_not_pass_hook(self) -> None:
        mock_post_load = MagicMock()
        logger = MagicMock()

        service = XrefLoadService(
            source=XrefSource.UNIPROT,
            logger=logger,
            ccds_post_load_service=mock_post_load,
        )

        with patch(
            "hgnc_xref_loader.services.xref_load_service.get_loader"
        ) as mock_get_loader:
            mock_loader_cls = MagicMock()
            mock_loader_instance = MagicMock()
            mock_loader_instance.run.return_value = 0
            mock_loader_cls.return_value = mock_loader_instance
            mock_get_loader.return_value = mock_loader_cls

            service.run()

            mock_loader_cls.assert_called_once_with()
            call_kwargs = mock_loader_cls.call_args.kwargs
            assert "post_load_hook" not in call_kwargs

    def test_ccds_without_post_load_service_does_not_pass_hook(self) -> None:
        logger = MagicMock()

        service = XrefLoadService(
            source=XrefSource.CCDS,
            logger=logger,
        )

        with patch(
            "hgnc_xref_loader.services.xref_load_service.get_loader"
        ) as mock_get_loader:
            mock_loader_cls = MagicMock()
            mock_loader_instance = MagicMock()
            mock_loader_instance.run.return_value = 0
            mock_loader_cls.return_value = mock_loader_instance
            mock_get_loader.return_value = mock_loader_cls

            service.run()

            mock_loader_cls.assert_called_once_with()
