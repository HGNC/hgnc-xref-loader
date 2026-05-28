"""MySQL driver validation for Ensembl database connectivity.

Enforces that only mysqlclient (MySQLdb) is used for Ensembl MySQL connections,
rejecting unsupported drivers such as mysql-connector-python and pymysql.
This validation runs at repository initialization time to fail fast on
misconfiguration rather than during query execution.
"""

from __future__ import annotations

from hgnc_xref_loader.ensembl_exceptions import EnsemblOrmDriverError

ALLOWED_DRIVERS: frozenset[str] = frozenset({"mysqldb", "mysqlclient"})
PROHIBITED_DRIVERS: frozenset[str] = frozenset({"mysqlconnector", "pymysql"})


def validate_mysql_driver(driver_name: str) -> None:
    """Validate that the given MySQL driver name is an allowed driver.

    Accepts mysqlclient and mysqldb driver names. Raises EnsemblOrmDriverError
    for known prohibited drivers (mysql-connector-python, pymysql) or any
    other unrecognised driver.

    Args:
        driver_name: The SQLAlchemy driver dialect name to validate.

    Raises:
        EnsemblOrmDriverError: If the driver is not in the allowed set.
    """
    normalised = driver_name.lower().replace("-", "").replace("_", "")

    if normalised in ALLOWED_DRIVERS:
        return

    if normalised in PROHIBITED_DRIVERS:
        raise EnsemblOrmDriverError(
            f"Unsupported MySQL driver '{driver_name}'. "
            f"Ensembl connections require mysqlclient (MySQLdb). "
            f"Prohibited drivers: mysql-connector-python, pymysql."
        )

    raise EnsemblOrmDriverError(
        f"Unknown MySQL driver '{driver_name}'. "
        f"Ensembl connections require mysqlclient (MySQLdb). "
        f"Allowed drivers: {', '.join(sorted(ALLOWED_DRIVERS))}."
    )
