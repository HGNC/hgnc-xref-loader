"""Repository factory functions for the HGNC xref-loader CLI.

Constructs concrete repository and service instances from application
settings. Called only by the CLI controller at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from hgnc_xref_loader.repositories.postgres_ccds_post_load_repository import (
    PostgresCcdsPostLoadRepository,
)
from hgnc_xref_loader.services.ccds_post_load_service import CcdsPostLoadService

if TYPE_CHECKING:
    from hgnc_xref_loader.config import Settings


def build_ccds_post_load_service(
    settings: Settings,
    session: Session,
) -> CcdsPostLoadService:
    """Build a CcdsPostLoadService from settings and a session.

    Constructs the Genew4Lock and PostgresCcdsPostLoadRepository
    required for CCDS post-load gene column mutations.

    Args:
        settings: Application configuration.
        session: Read-write SQLAlchemy session for mutations.

    Returns:
        A configured CcdsPostLoadService.
    """
    from shared import genew4_lock

    lock_repo = genew4_lock.Genew4LockSqlRepository(session=session)
    lock = genew4_lock.Genew4Lock(repository=lock_repo, name="ccds_loader")

    post_load_repo = PostgresCcdsPostLoadRepository(session=session)

    return CcdsPostLoadService(lock=lock, post_load_repo=post_load_repo)
