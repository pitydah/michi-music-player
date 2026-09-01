"""Playlist visual asset transaction contract (PL-FINAL-A07 / 10-10-FINAL-01).

``PreparedPlaylistAsset`` is the SINGLE contract between the playlist
artwork store and the playlist service: path + role + whether THIS
operation created the managed file. Only ``created_by_operation == True``
candidates may enter rollback cleanup ownership — content-addressed
reuse (same bytes → same file) is NEVER cleaned by a failed transaction.

``PlaylistArtworkStoreContract`` is the CANONICAL store abstraction the
Service depends on. It lives in the application layer (filesystem/
transaction ownership semantics) and is deliberately separate from
``ports.PlaylistArtworkStorePort``, which is frozen by the M11.3F engine
adapter gate (hash ``2e42f5056b3a3fce``) — the Service NEVER uses the
frozen port for asset preparation. Exactly ONE contractual definition of
asset preparation exists: this module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
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


class PlaylistArtworkStoreContract(ABC):
    """PL-10-FINAL-01: the ONE contract PlaylistService depends on.

    A store that does not implement ``prepare_candidate`` CANNOT be used
    by the Service — construction fails fast (TypeError) instead of a
    runtime getattr fallback that would invent ownership. The legacy
    ``prepare_cover`` / ``prepare_hero`` pair is intentionally NOT part
    of this abstraction (convenience wrappers may exist on concrete
    stores for historical tests only).
    """

    @abstractmethod
    def prepare_candidate(
        self,
        playlist_id: str,
        source_path: Path | str,
        role: AssetRole,
    ) -> PreparedPlaylistAsset | None:
        """Materialize the immutable content-addressed candidate; None on
        rejection. ``created_by_operation`` distinguishes a newly created
        managed file from an idempotent REUSE of identical bytes."""
        ...

    @abstractmethod
    def delete_managed_asset(
        self,
        playlist_id: str,
        role: AssetRole,
        managed_path: str,
    ) -> bool:
        """Retire a managed asset by reference (post-commit). True when
        the file was removed; ownership must be fail-closed."""
        ...
