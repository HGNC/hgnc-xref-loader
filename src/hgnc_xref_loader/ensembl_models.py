"""Ensembl ORM consumer models for the HGNC cross-reference loader.

Defines Pydantic models representing cross-reference data exchanged between
the Ensembl repository layer and service layer. These models decouple services
from concrete ORM classes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Xref(BaseModel):
    """A cross-reference entry from an Ensembl gene.

    Represents a single cross-reference linking an Ensembl gene to an
    external database entry.

    Attributes:
        source: The external database name (e.g. "HGNC", "UniProt").
        source_id: The identifier in the external database.
        description: A human-readable description of the cross-reference.
    """

    source: str = Field(description="External database name")
    source_id: str = Field(description="Identifier in the external database")
    description: str = Field(description="Human-readable description")
