"""Retry-at-boundary mechanisms with idempotent semantics for repository operations.

Provides a decorator that retries database operations on transient connection
errors exactly once, ensuring idempotent behaviour suitable for Cloud Run Jobs
that may experience mid-run maintenance events.
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from sqlalchemy.exc import OperationalError


def retry_on_connection_error(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorate a function to retry once on transient OperationalError.

    Cloud Run Job maintenance events can break outbound VPC connections mid-run.
    This decorator catches OperationalError and retries the function exactly once.
    Non-transient errors are re-raised without retry.

    Args:
        func: The function to wrap.

    Returns:
        The wrapped function with single-retry semantics.

    Example::

        @retry_on_connection_error
        def fetch_records(session: Session) -> list[Record]:
            return session.execute(select(Record)).scalars().all()
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except OperationalError:
            return func(*args, **kwargs)

    return wrapper
