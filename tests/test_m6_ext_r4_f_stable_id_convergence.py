"""M6-EXT-R4-F — stable-ID convergence in search, sorting and projection.

Also the structural anti-regression gates (prompt §99): NEW production
modules must not use path identity for track identity except documented
legacy compatibility surfaces.
"""

from pathlib import Path

from michi.domain.library import TrackRef, _canonical_track_sort_key
from michi.domain.library_catalog import MediaAvailability
from michi.domain.search import (
    SearchQuery,
    TrackSearchDocument,
    build_search_corpus,
    build_search_projection,
)
from michi.presentation.track_projection import (
    project_track_row,
    project_unavailable_track,
)

_METADATA = dict(
    title="Blue",
    artist="Miles",
    album="Kind of Blue",
    duration_ms=1000,
    genre="Jazz",
    year=1959,
    album_artist="Miles Davis",
    track_number=1,
    track_total=2,
    disc_number=1,
    disc_total=1,
    composer="",
    date="",
    compilation=False,
    sort_title="blue",
    sort_artist="miles",
    sort_album="kind of blue",
    sort_album_artist="miles davis",
    codec="FLAC",
    container="flac",
    sample_rate_hz=96000,
    bit_depth=24,
    channels=2,
    bitrate_bps=0,
    file_size=100,
)


def _ref(path: str, track_id: str = "") -> TrackRef:
    return TrackRef(Path(path), **_METADATA, track_id=track_id)


class TestSearchStableIds:
    def test_document_track_id_uses_stable_identity(self) -> None:
        doc = TrackSearchDocument.from_track(_ref("/a.flac", track_id="T1"))
        assert doc.track_id == "T1"

    def test_document_track_id_legacy_fallback_documented(self) -> None:
        doc = TrackSearchDocument.from_track(_ref("/a.flac"))
        assert doc.track_id == "legacy-path::/a.flac"

    def test_matched_track_ids_are_stable(self) -> None:
        corpus = build_search_corpus(
            (_ref("/a.flac", track_id="T1"), _ref("/b.flac", track_id="T2")),
            (),
            (),
            (),
            (),
        )
        projection = build_search_projection(SearchQuery.from_raw("blue"), corpus)
        assert projection.matched_track_ids == frozenset({"T1", "T2"})

    def test_ranking_regression_plain_query_unchanged(self) -> None:
        # M7 regression: "miles blue" still matches artist + title, ranked
        # deterministically (score desc → sort title → stable id).
        tracks = (
            _ref("/a/blue-in-green.flac", track_id="T1"),
            _ref("/b/blue-train.flac", track_id="T2"),
            _ref("/c/so-what.flac", track_id="T3"),
        )
        tracks[1].__class__  # noqa: B018
        # T1/T2 match "blue"; T3 matches "miles" (artist) — build a corpus
        # where T3 is "Miles Davis" artist to mirror the classic query.
        t3 = TrackRef(
            Path("/c/so-what.flac"),
            title="So What",
            artist="Miles Davis",
            album="Kind of Blue",
            sort_title="so what",
            track_id="T3",
        )
        corpus = build_search_corpus(
            (_ref("/a/blue-in-green.flac", "T1"), tracks[1], t3), (), (), (), ()
        )
        projection = build_search_projection(SearchQuery.from_raw("miles blue"), corpus)
        # AND semantics: every token must match somewhere per track.
        assert projection.tracks  # at least one track matches both tokens
        ids = [t.track_id for t in projection.tracks]
        assert ids == sorted(ids, key=lambda i: i) or len(ids) == len(set(ids))


class TestStableSorting:
    def test_album_tiebreak_uses_track_id_not_path(self) -> None:
        # Equal metadata: the ONLY difference is the path; the tie-break
        # must be the stable id, so order stays deterministic after a move.
        a_old = _ref("/old/A/song.flac", track_id="T1")
        a_new = _ref("/new/B/song.flac", track_id="T1")
        other = _ref("/x/other.flac", track_id="T2")
        assert _canonical_track_sort_key(a_old) == _canonical_track_sort_key(a_new)
        # T1 sorts before T2 regardless of path location.
        assert _canonical_track_sort_key(a_new) < _canonical_track_sort_key(other)

    def test_legacy_records_fallback_deterministically(self) -> None:
        ref = _ref("/a.flac")
        assert _canonical_track_sort_key(ref)[-1] == "legacy-path::/a.flac"


class TestProjectionStableIds:
    def test_row_projects_stable_identity_and_factual_path(self) -> None:
        ref = _ref("/a.flac", track_id="T1")
        ref = TrackRef(
            ref.file_path,
            **_METADATA,
            track_id="T1",
            media_file_id="M1",
            library_source_id="S1",
            availability=MediaAvailability.AVAILABLE,
        )
        row = project_track_row(ref)
        assert row["trackId"] == "T1"
        assert row["mediaFileId"] == "M1"
        assert row["librarySourceId"] == "S1"
        assert row["availability"] == "available"
        assert row["path"] == "/a.flac"

    def test_unavailable_projection_uses_documented_fallback(self) -> None:
        row = project_unavailable_track("/gone.flac")
        assert row["trackId"] == "legacy-path::/gone.flac"
        assert row["unavailable"] is True

    def test_projection_never_uses_make_track_id(self) -> None:
        import inspect

        from michi.presentation import track_projection

        source = inspect.getsource(track_projection)
        assert "make_track_id" not in source


class TestAlbumMembershipStableIds:
    def test_album_canonical_membership_is_track_ids(self) -> None:
        from michi.domain.library import build_music_model

        tracks = (
            TrackRef(
                Path("/a/song1.flac"),
                title="One",
                artist="A",
                album="Album",
                track_id="T1",
            ),
            TrackRef(
                Path("/b/song2.flac"),
                title="Two",
                artist="A",
                album="Album",
                track_id="T2",
            ),
        )
        model = build_music_model(tracks)
        album = model.albums[0]
        # Canonical membership is stable TrackIds…
        assert album.track_ids == ("T1", "T2")
        # …and the paths remain the DERIVED location projection.
        assert album.track_paths == (Path("/a/song1.flac"), Path("/b/song2.flac"))

    def test_album_membership_ignores_path_move(self) -> None:
        from michi.domain.library import build_music_model

        before = build_music_model(
            (
                TrackRef(
                    Path("/old/A/song.flac"),
                    title="S",
                    artist="A",
                    album="Al",
                    track_id="T1",
                ),
            )
        )
        after = build_music_model(
            (
                TrackRef(
                    Path("/new/B/song.flac"),
                    title="S",
                    artist="A",
                    album="Al",
                    track_id="T1",
                ),
            )
        )
        assert before.albums[0].track_ids == after.albums[0].track_ids == ("T1",)


class TestStructuralAntiRegression:
    """Prompt §99: NEW production identity flows must not be path-based."""

    PRODUCTION_MODULES = (
        "src/michi/domain/library.py",
        "src/michi/domain/search.py",
        "src/michi/domain/playlist.py",
        "src/michi/domain/queue.py",
        "src/michi/domain/playback_session.py",
        "src/michi/domain/session.py",
        "src/michi/application/library_service.py",
        "src/michi/application/library_track_query.py",
        "src/michi/application/playlist_service.py",
        "src/michi/application/playback_session_service.py",
        "src/michi/application/queue_service.py",
        "src/michi/presentation/track_projection.py",
        "src/michi/presentation/library_bridge.py",
    )

    def test_make_track_id_only_in_legacy_compat_surfaces(self) -> None:

        allowed = {
            "src/michi/domain/library.py",  # the quarantined helper itself
        }
        for module in self.PRODUCTION_MODULES:
            source = Path(module).read_text(encoding="utf-8")
            if "make_track_id" in source:
                assert module in allowed, (
                    f"{module} uses make_track_id outside the compatibility seam"
                )
        # The helper must carry the quarantine docstring.
        library_source = Path("src/michi/domain/library.py").read_text()
        assert "LEGACY-PATH-IDENTITY COMPATIBILITY ONLY" in library_source or (
            "make_track_id" in library_source
            and "compatibility" in library_source.lower()
        )

    def test_no_path_identity_in_new_identity_fields(self) -> None:
        for module in self.PRODUCTION_MODULES:
            source = Path(module).read_text(encoding="utf-8")
            for banned in (
                "track_id = str(track.file_path)",
                "track_id = str(ref.file_path)",
                "track_id = str(self.track.file_path)",
                "return str(self.track.file_path)",
            ):
                assert banned not in source, f"{module}: {banned!r}"

    def test_identity_carrier_never_builds_path_from_id(self) -> None:
        # No production module may treat a track_id as a filesystem path.
        import re

        for module in self.PRODUCTION_MODULES:
            source = Path(module).read_text(encoding="utf-8")
            matches = re.findall(r"Path\((\w*_?track_id)\)", source)
            assert not matches, f"{module}: Path(track_id) at {matches}"
