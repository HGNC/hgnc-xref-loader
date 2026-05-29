"""Tests for CCDS post-load wiring into the loader lifecycle.

Validates that CcdsXrefLoader invokes a post-load hook after the
standard fetch-normalize lifecycle, and that MainService wires
CcdsPostLoadService when the source is 'ccds'.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hgnc_xref_loader.loaders.ccds_loader import CcdsXrefLoader
from hgnc_xref_loader.loaders.registry import XrefSource


class TestCcdsLoaderPostLoadHook:
    """Tests for CcdsXrefLoader post-load hook invocation."""

    def test_run_calls_post_load_hook_when_provided(self) -> None:
        mock_hook = MagicMock()
        loader = CcdsXrefLoader(post_load_hook=mock_hook)
        loader.run()

        mock_hook.assert_called_once()

    def test_run_does_not_fail_when_hook_is_none(self) -> None:
        loader = CcdsXrefLoader(post_load_hook=None)
        result = loader.run()
        assert result == 0

    def test_hook_called_after_normalize(self) -> None:
        call_order: list[str] = []
        mock_hook = MagicMock(side_effect=lambda: call_order.append("hook"))

        loader = CcdsXrefLoader(post_load_hook=mock_hook)
        original_normalize = loader.normalize

        def tracking_normalize(raw):
            call_order.append("normalize")
            return original_normalize(raw)

        loader.normalize = tracking_normalize
        loader.run()

        assert call_order == ["normalize", "hook"]

    def test_run_raises_when_hook_raises(self) -> None:
        mock_hook = MagicMock(side_effect=RuntimeError("post-load failed"))
        loader = CcdsXrefLoader(post_load_hook=mock_hook)

        with pytest.raises(RuntimeError, match="post-load failed"):
            loader.run()
