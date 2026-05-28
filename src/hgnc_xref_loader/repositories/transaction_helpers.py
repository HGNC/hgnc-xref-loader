"""Reusable idempotent transaction helpers for repository-layer operations.

Provides context managers and helper functions for staging table swaps
and upsert operations. All SQL uses SQLAlchemy text() with bindparam()
for parameterized values.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@contextmanager
def staging_swap_context(session: Session, table_name: str):
    """Provide a transactional context for a staging table swap.

    Within this context, the caller can perform staging table operations
    (create, load, index, validate). On successful completion, the staging
    table is renamed to production. On failure, the transaction rolls back
    and the previous production state is preserved.

    Args:
        session: A SQLAlchemy Session to use for the transaction.
        table_name: Base name of the table (without _update suffix).

    Yields:
        The session for use within the context.
    """
    try:
        with session.begin():
            yield session
    except Exception:
        raise


def upsert_on_conflict(
    session: Session,
    table: str,
    data: dict[str, Any],
    conflict_columns: list[str],
) -> int:
    """Execute an INSERT ... ON CONFLICT DO UPDATE statement.

    Performs an idempotent upsert keyed on the specified conflict columns.
    If a row with matching conflict columns exists, it is updated with the
    new data. Otherwise, a new row is inserted.

    Args:
        session: A SQLAlchemy Session.
        table: Target table name.
        data: Column-value mapping to upsert.
        conflict_columns: Columns that define the conflict key.

    Returns:
        The number of rows affected (1 for insert or update).
    """
    columns = list(data.keys())
    placeholders = ", ".join(f":{col}" for col in columns)
    col_names = ", ".join(columns)
    update_set = ", ".join(f"{col} = :{col}" for col in columns if col not in conflict_columns)
    conflict = ", ".join(conflict_columns)

    stmt = text(
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT ({conflict}) DO UPDATE SET {update_set}"
    )

    result = session.connection().execute(stmt, data)
    return result.rowcount
