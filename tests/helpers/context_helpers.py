"""Helpers for context tests — isolated ContextService with tmp_path."""

from core.context import context_repository as repo
from core.context.context_service import ContextService


def make_context_service(tmp_path, db=None, playback=None):
    db_path = tmp_path / "context.sqlite"
    repo.override_db_path(str(db_path))
    return ContextService(db=db, playback=playback)


def cleanup_context_repo():
    repo.close()
    repo.override_db_path(None)
