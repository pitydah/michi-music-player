"""Playlist visual asset transaction contract (PL-FINAL-A07).

``PreparedPlaylistAsset`` is the SINGLE contract between the playlist
artwork store and the playlist service: path + role + whether THIS
operation created the managed file. Only ``created_by_operation == True``
candidates may enter rollback cleanup ownership — content-addressed
reuse (same bytes → same file) is NEVER cleaned by a failed transaction.

It lives in the application layer because it carries filesystem/
transaction ownership semantics, not musical domain semantics.
"""

from dataclasses import dataclass
from typing import Literal

AssetRole = Literal["cover", "hero"]


@dataclass(frozen=True)
class PreparedPlaylistAsset:
    """Transaction-owned asset candidate contract.

    ``created_by_operation`` is the KILLCRITIC fact that makes rollback
    safe for content-addressed storage: a prepared path is NOT necessarily
    a new file — content-addressed stores REUSE an existing file when the
    exact same bytes already exist. Only candidates with
    ``created_by_operation == True`` may ever enter rollback cleanup
    ownership. Reused assets, previously committed assets, other
    playlists' assets and unowned paths are NEVER deleted by a failed
    transaction.
    """

    path: str
    role: AssetRole
    created_by_operation: bool
