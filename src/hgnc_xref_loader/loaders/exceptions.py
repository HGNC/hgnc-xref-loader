"""Domain exceptions for the loaders package.

Defines exceptions specific to the xref loader lifecycle, including unknown
source configuration and loader runtime failures.
"""

from __future__ import annotations

from hgnc_xref_loader.exceptions import ServiceError


class UnknownSourceError(ServiceError):
    """Raised when an unrecognised XREF_SOURCE value is configured.

    Indicates that the configured source name does not match any member
    of the XrefSource enum and therefore has no registered loader.
    """


class LoaderRuntimeError(ServiceError):
    """Raised when a loader execution fails during its run lifecycle.

    Wraps lower-level exceptions from individual loader implementations
    to provide a consistent error boundary at the service layer.
    """
