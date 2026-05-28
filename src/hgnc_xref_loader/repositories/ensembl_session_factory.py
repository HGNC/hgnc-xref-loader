"""Ensembl MySQL engine and session factory for the HGNC cross-reference loader.

Creates SQLAlchemy engines and session factories for the Ensembl MySQL database
using mysqlclient driver via ensembl-orm utilities. Configured for Cloud Run Job
resilience with pool_pre_ping and pool_recycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from hgnc_xref_loader.config import EnsemblSettings

POOL_PRE_PING = True
POOL_RECYCLE_SECONDS = 3600
POOL_SIZE = 5
MAX_OVERFLOW = 10

MYSQL_DRIVER_PREFIX = "mysql+mysqldb://"


def create_ensembl_engine(settings: EnsemblSettings):
    """Create a SQLAlchemy engine for the Ensembl MySQL database.

    Uses mysqlclient (mysqldb) driver only. Configures connection pooling
    for Cloud Run Job resilience with pool_pre_ping and pool_recycle.

    Args:
        settings: Ensembl database connection settings.

    Returns:
        A SQLAlchemy Engine instance configured for mysqlclient.
    """
    dsn_dict = settings.dsn()
    host = dsn_dict["host"]
    port = dsn_dict["port"]
    user = dsn_dict["user"]
    database = dsn_dict["database"]
    password = dsn_dict.get("password", "")

    if password:
        url = f"{MYSQL_DRIVER_PREFIX}{user}:{password}@{host}:{port}/{database}"
    else:
        url = f"{MYSQL_DRIVER_PREFIX}{user}@{host}:{port}/{database}"

    return create_engine(
        url,
        pool_pre_ping=POOL_PRE_PING,
        pool_recycle=POOL_RECYCLE_SECONDS,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
    )


def create_ensembl_session_factory(engine):
    """Create a session factory for the Ensembl MySQL database.

    Args:
        engine: A SQLAlchemy Engine instance for Ensembl MySQL.

    Returns:
        A callable session factory producing Session instances.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)
