"""CLI entrypoint for the HGNC cross-reference loader batch job."""

from __future__ import annotations

import logging
import sys

from hgnc_xref_loader.config import Settings
from hgnc_xref_loader.ensembl_exceptions import (
    EnsemblDbResolutionError,
    EnsemblOrmDriverError,
    EnsemblOrmMissingModelError,
)
from hgnc_xref_loader.exceptions import ConfigError, ServiceError
from hgnc_xref_loader.loaders.exceptions import (
    LoaderRuntimeError,
    UnknownSourceError,
)
from hgnc_xref_loader.loaders.registry import XrefSource
from hgnc_xref_loader.logging_config import configure_logging
from hgnc_xref_loader.services.xref_load_service import XrefLoadService


def main(argv: list[str] | None = None) -> int:
    """Run the HGNC cross-reference loader batch job.

    This function is the controller for the batch job. It handles
    configuration loading, logging setup, service wiring, and
    exit-code mapping. It MUST NOT contain business logic.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 for success, 1 for unexpected error,
        2 for configuration error, 3 for domain error,
        4 for Ensembl driver error, 5 for Ensembl model error,
        6 for Ensembl DB resolution error.
    """
    argv = argv or sys.argv[1:]
    configure_logging()

    try:
        settings = Settings()
    except ConfigError:
        return 2
    except Exception:
        return 2

    try:
        source = _resolve_source(settings.runtime.xref_source)
    except (ValueError, ConfigError):
        return 2

    logger = logging.getLogger("hgnc_xref_loader")

    ccds_post_load = None
    if source == XrefSource.CCDS:
        from hgnc_xref_loader.repositories import wiring as _wiring
        from hgnc_xref_loader.repositories.session_factory import (
            create_genew4_engine as _create_engine,
            create_session_factory as _create_session_factory,
        )

        _engine = _create_engine(settings.genew4)
        _session = _create_session_factory(_engine)()

        ccds_post_load = _wiring.build_ccds_post_load_service(
            settings=settings,
            session=_session,
        )

    try:
        service = XrefLoadService(
            source=source,
            logger=logger,
            ccds_post_load_service=ccds_post_load,
        )
        service.run()
    except ConfigError:
        return 2
    except EnsemblOrmDriverError:
        return 4
    except EnsemblOrmMissingModelError:
        return 5
    except EnsemblDbResolutionError:
        return 6
    except (UnknownSourceError, LoaderRuntimeError, ServiceError):
        return 3
    except Exception:
        return 1
    return 0


def _resolve_source(raw: str) -> XrefSource:
    """Resolve a raw XREF_SOURCE string to an XrefSource enum member.

    Args:
        raw: The raw source string from configuration.

    Returns:
        The matching XrefSource enum member.

    Raises:
        ValueError: If the string does not match any XrefSource member.
    """
    if not raw:
        raise ValueError("XREF_SOURCE is required but was not provided")
    return XrefSource(raw)
