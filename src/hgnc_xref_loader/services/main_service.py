"""Main service for the HGNC cross-reference loader."""

from typing import TYPE_CHECKING

from hgnc_xref_loader.services.base_service import Service

if TYPE_CHECKING:
    from hgnc_xref_loader.config import Settings


class MainService(Service):
    """Orchestrate the HGNC cross-reference loading workflow.

    This service coordinates the steps required to load cross-reference
    data. All database access is delegated to injected repositories.
    """

    def __init__(self, settings: "Settings") -> None:
        self._settings = settings

    @classmethod
    def from_settings(cls, settings: "Settings") -> "MainService":
        """Construct a MainService from a Settings instance.

        Args:
            settings: Application configuration.

        Returns:
            A configured MainService ready to run.
        """
        return cls(settings=settings)

    def run(self) -> None:
        """Execute the cross-reference loading workflow."""
