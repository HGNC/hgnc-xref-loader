"""Allow running as ``python -m hgnc_xref_loader``."""

from hgnc_xref_loader.cli import main

raise SystemExit(main())
