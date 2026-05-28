"""Domain-specific exception hierarchy for the HGNC cross-reference loader."""


class ServiceError(Exception):
    """Base exception for all domain errors."""


class ConfigError(ServiceError):
    """Raised when configuration is invalid or missing."""


class RepositoryError(ServiceError):
    """Raised when a database or data access operation fails."""
