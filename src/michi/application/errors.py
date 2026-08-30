"""Application-layer contractual errors (TRUE FINAL SEAL R2 P1-04).

Dependency direction: Infrastructure raises → Application defines →
Presentation translates. Domain NEVER knows about persistence failures —
it owns musical/domain concepts only.
"""


class PlaylistNameInvalidError(ValueError):
    """Playlist name is empty/whitespace — a LOGICAL validation result,
    never a persistence failure (R3-04)."""


class PlaylistNameConflictError(ValueError):
    """A playlist with this name already exists — a LOGICAL validation
    result, never a persistence failure (R3-04)."""


class PlaylistPersistenceError(RuntimeError):
    """An authoritative playlist write failed (P0-02).

    Truthful persistence: a mutation either commits or raises — the
    in-memory state rolls back to the last persisted snapshot and the
    caller never sees a false success.

    Presentation boundary contract: this error is translated at the
    QObject/QML edge (PlaylistsBridge._run_mutation) into a stable
    operation failure code; it NEVER escapes raw into QML.
    """
