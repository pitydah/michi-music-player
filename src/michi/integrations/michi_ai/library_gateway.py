"""Read-only LibraryGateway backed by the Player's canonical library state."""

from __future__ import annotations

from michi_ai.integration import (
    ErrorCode,
    LibraryStatusV1,
    LibraryTrackV1,
    OperationResult,
)

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.domain.library import TrackRef
from michi.domain.search import (
    SearchQuery,
    build_search_corpus,
    build_search_projection,
)


class PlayerLibraryGateway:
    """Projects canonical Player state without mutating visible UI search."""

    def __init__(
        self,
        library: LibraryService,
        resolver: LibraryTrackResolver,
    ) -> None:
        self._library = library
        self._resolver = resolver

    def search(self, query: str) -> OperationResult[list[dict[str, object]]]:
        try:
            state = self._library.state
            corpus = build_search_corpus(
                state.tracks,
                state.albums,
                state.artists,
                state.genres,
                state.composers,
            )
            projection = build_search_projection(SearchQuery.from_raw(query), corpus)
            tracks = [
                self._track_projection(ref) for ref in projection.tracks if ref.track_id
            ]
        except Exception:
            return OperationResult.failure(
                ErrorCode.GATEWAY_ERROR,
                "Player library search failed safely",
            )
        return OperationResult.success(tracks)

    def get_track(self, track_id: str) -> OperationResult[dict[str, object]]:
        try:
            ref = self._resolver.resolve_ref(track_id)
            if ref is None or not ref.track_id:
                return OperationResult.failure(
                    ErrorCode.NO_MATCH,
                    "Player library track was not found",
                )
            track = self._track_projection(ref)
        except Exception:
            return OperationResult.failure(
                ErrorCode.GATEWAY_ERROR,
                "Player library track lookup failed safely",
            )
        return OperationResult.success(track)

    def get_status(self) -> OperationResult[dict[str, object]]:
        try:
            state = self._library.state
            status = LibraryStatusV1(
                total_tracks=len(state.tracks),
                total_artists=len(state.artists),
                total_albums=len(state.albums),
                available=True,
                scan_status=state.scan_status.name.lower(),
            )
        except Exception:
            return OperationResult.failure(
                ErrorCode.GATEWAY_ERROR,
                "Player library status failed safely",
            )
        return OperationResult.success(status)

    def _track_projection(self, ref: TrackRef) -> LibraryTrackV1:
        availability = self._resolver.effective_availability(ref)
        return LibraryTrackV1(
            track_id=ref.track_id,
            title=ref.title or ref.display_name,
            artist=ref.artist,
            album=ref.album,
            duration_ms=ref.duration_ms,
            availability=availability.value,
        )
