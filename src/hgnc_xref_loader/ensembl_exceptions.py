"""Ensembl-specific exception hierarchy for the HGNC cross-reference loader.

Defines domain exceptions for Ensembl ORM integration failures including
missing models, unsupported drivers, and database resolution errors.
"""

from __future__ import annotations

from hgnc_xref_loader.exceptions import RepositoryError


class EnsemblOrmMissingModelError(RepositoryError):
    """Raised when required Ensembl ORM models are not available.

    Indicates that the ensembl-orm library is missing expected model classes
    or that the installed version does not provide the required schema mappings.
    """


class EnsemblOrmDriverError(RepositoryError):
    """Raised when an unsupported MySQL driver is detected for Ensembl connectivity.

    Ensembl MySQL connections must use mysqlclient (MySQLdb) exclusively.
    This exception is raised when mysql-connector-python or pymysql are detected.
    """


class EnsemblDbResolutionError(RepositoryError):
    """Raised when Ensembl database release resolution fails.

    Indicates that the appropriate Ensembl core database could not be determined
    from the available configuration, schema metadata, or connectivity.
    """
