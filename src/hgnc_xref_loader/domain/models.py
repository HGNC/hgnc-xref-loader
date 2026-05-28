"""XrefRecord domain model and LoaderMetrics for xref source adapters.

Defines the canonical cross-reference record schema with automatic
normalization (whitespace trimming, case normalization) and a metrics
container for per-source row counters used in SLO tracking.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class XrefRecord(BaseModel):
    """A normalised cross-reference record from an external source.

    Represents a single cross-reference linking an HGNC gene to an
    external database entry. Fields are automatically normalised on
    construction: whitespace is trimmed, source is lowercased, and
    empty optional strings become None.

    Records are sortable by (hgnc_id, external_id) for deterministic
    ordering during bulk loads.

    Attributes:
        hgnc_id: HGNC identifier (e.g. ``HGNC:1100``).
        external_id: Identifier in the external database.
        source: Lowercased external database name (e.g. ``ensembl``).
        symbol: Optional HGNC gene symbol.
        status: Optional record status (e.g. ``approved``).
    """

    hgnc_id: str = Field(description="HGNC identifier")
    external_id: str = Field(description="External database identifier")
    source: str = Field(description="External database name (lowercased)")
    symbol: str | None = Field(default=None, description="HGNC gene symbol")
    status: str | None = Field(default=None, description="Record status")

    @field_validator("hgnc_id", "external_id", mode="before")
    @classmethod
    def trim_identifiers(cls, v: str) -> str:
        return v.strip()

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("symbol", "status", mode="before")
    @classmethod
    def trim_optional_fields(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip() or None

    def __lt__(self, other: XrefRecord) -> bool:
        return (self.hgnc_id, self.external_id) < (other.hgnc_id, other.external_id)

    def __le__(self, other: XrefRecord) -> bool:
        return (self.hgnc_id, self.external_id) <= (other.hgnc_id, other.external_id)

    def __gt__(self, other: XrefRecord) -> bool:
        return (self.hgnc_id, self.external_id) > (other.hgnc_id, other.external_id)

    def __ge__(self, other: XrefRecord) -> bool:
        return (self.hgnc_id, self.external_id) >= (other.hgnc_id, other.external_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, XrefRecord):
            return NotImplemented
        return (
            self.hgnc_id == other.hgnc_id
            and self.external_id == other.external_id
            and self.source == other.source
        )


class LoaderMetrics(BaseModel):
    """Per-source row counters for xref loader runs.

    Tracks total, parsed, and skipped row counts for structured logging
    and SLO reporting.

    Attributes:
        source: The xref source name these metrics apply to.
        total_rows: Total rows encountered in the source data.
        parsed_rows: Rows successfully parsed and normalised.
        skipped_rows: Rows skipped due to errors or malformed data.
    """

    source: str = Field(description="Xref source name")
    total_rows: int = Field(default=0, description="Total rows encountered")
    parsed_rows: int = Field(default=0, description="Successfully parsed rows")
    skipped_rows: int = Field(default=0, description="Skipped rows")
