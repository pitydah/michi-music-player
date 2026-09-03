"""PLAYLISTS IDENTITY RECOVERY — legacy (V1/V2) membership convergence.

The identity migration (``LibraryIdentityMigration``) runs only while the
catalog is being created. An existing installation upgrading to the
TrackId-based Playlist architecture may already HAVE a catalog while its
playlists are still path-only (V2) — this module closes that gap at
startup: every path-only member whose path the CURRENT catalog resolves
is upgraded to a real ``PlaylistTrackReference(track_id, path)``.

Rules (REVIEW SEAL):
- The TrackId comes from the catalog (the track currently owning that
  path) — never fabricated, never guessed via legacy-path tokens.
- A path the catalog does not resolve stays a legacy member (""
  track_id) — honest, never deleted, never invented.
- A playlist that already carries TrackIds is untouched.
- Convergence persists ONCE per playlist that actually changed (a no-op
  startup writes nothing).
"""

import logging
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playlist_service import PlaylistService
from michi.domain.playlist import PlaylistTrackReference

logger = logging.getLogger(__name__)


def converge_legacy_playlist_membership(
    playlists: PlaylistService, library: LibraryService
) -> int:
    """Upgrade path-only playlist memberships against the existing
    catalog. Returns the number of playlists durably upgraded (0 → zero
    writes)."""
    upgraded_count = 0
    for playlist in playlists.playlists:
        if any(playlist.track_ids):
            continue  # ya TrackId-native (V3 o convergida); ("","") es legacy
        references = []
        dirty = False
        for ref in playlist.references():
            if ref.track_id:
                references.append(ref)
                continue
            if not ref.fallback_path:
                references.append(ref)
                continue
            track = library.resolve_trackref(Path(ref.fallback_path))
            if track is not None and getattr(track, "track_id", ""):
                references.append(
                    PlaylistTrackReference(
                        track_id=track.track_id,
                        fallback_path=ref.fallback_path,
                    )
                )
                dirty = True
                continue
            references.append(ref)  # path no resuelto: legacy honesto
        if dirty and playlists.replace_membership(playlist.playlist_id, references):
            upgraded_count += 1
    if upgraded_count:
        logger.info(
            "converged %d legacy playlist(s) to TrackId membership",
            upgraded_count,
        )
    return upgraded_count
