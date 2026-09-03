"""PLAYLISTS POST-MERGE IDENTITY RECOVERY (Iteración 1) — seam
service + persistence.

Restores the M6-EXT-R4-H contract that the fcd6710 semantic integration
replaced: ``PlaylistTrackReference(track_id, fallback_path)`` is the
PRODUCTIVE membership seam again (TrackId = stable identity, path =
location snapshot), persistence emits V3
{"version": 3, "tracks": [{"track_id", "fallback_path"}]} with
``track_paths`` kept ONLY as a derived compatibility projection, and a
V3 record is NEVER downgraded to V2.

Invariants sealed here (RED antes del fix):
- create_playlist_with_references / add_track_references (API TrackId);
- dedupe por TrackId cuando está presente (un track reubicado con el
  MISMO TrackId y path distinto NO duplica);
- remove/move mantienen track_ids y track_paths ALINEADOS por índice;
- V3 roundtrip durable: ids sobreviven restart (repo sqlite real);
- V3 nunca degradado: cargar V3 → mutar → guardar → sigue V3 con ids;
- V3 preserva los campos premium de main (description/appearance/focal);
- loader tolerante V1 + V2 (ids vacíos, id determinístico) sin writeback;
- APIs legacy path-only (add_track/add_tracks/insert_track) siguen
  funcionando como proyección (seals 10/10 intactos).
"""

import json

from michi.application.playlist_service import PlaylistService
from michi.domain.playlist import (
    Playlist,
    PlaylistTrackReference,
    legacy_playlist_id,
)
from michi.infrastructure.playlists import (
    PLAYLIST_PERSISTENCE_VERSION,
    SqlitePlaylistsRepository,
    _decode_playlist_entry,
)


class _CapturePort:
    """In-memory port that keeps the canonical V3 payload RAW — lets the
    tests assert the exact persisted shape (not just in-memory state)."""

    def __init__(self, raw: list | None = None) -> None:
        self.raw: list = list(raw) if raw is not None else []
        self.saved = 0

    def load(self) -> tuple[Playlist, ...]:
        return tuple(
            playlist
            for entry in self.raw
            if (playlist := _decode_playlist_entry(entry)) is not None
        )

    def save(self, playlists: tuple[Playlist, ...]) -> None:
        self.raw = json.loads(json.dumps(self._payload(playlists)))
        self.saved += 1

    def save_state(self, playlists, navigation) -> None:
        self.save(playlists)

    def load_navigation(self):
        from michi.domain.playlist import PlaylistNavigationState

        return PlaylistNavigationState()

    def save_navigation(self, state) -> None:
        del state

    def _payload(self, playlists: tuple[Playlist, ...]) -> list[dict]:
        # MISMA forma que el repo productivo (nunca un shape de test).
        from michi.infrastructure.playlists import _payload_for

        return _payload_for(playlists)


def _ref(track_id: str = "", path: str = "") -> PlaylistTrackReference:
    return PlaylistTrackReference(track_id=track_id, fallback_path=path)


class TestReferencesApi:
    def test_create_playlist_with_references_keeps_ids_and_paths(self) -> None:
        port = _CapturePort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist_with_references(
            "Mix", [_ref("T1", "/music/a.flac"), _ref("", "/legacy.flac")]
        )
        assert playlist.track_ids == ("T1", "")
        assert playlist.track_paths == ("/music/a.flac", "/legacy.flac")
        # Persistencia: el payload emite V3 con tracks + proyección paths.
        assert port.raw[0]["version"] == 3
        assert port.raw[0]["tracks"] == [
            {"track_id": "T1", "fallback_path": "/music/a.flac"},
            {"track_id": "", "fallback_path": "/legacy.flac"},
        ]
        assert port.raw[0]["track_paths"] == ["/music/a.flac", "/legacy.flac"]

    def test_add_track_references_dedupes_by_track_id_not_path(self) -> None:
        """El MISMO TrackId con path distinto (archivo reubicado) NO duplica:
        la identidad manda sobre la ubicación."""
        port = _CapturePort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist_with_references(
            "Mix", [_ref("T1", "/Music/A/song.flac")]
        )
        added = service.add_track_references(
            playlist.playlist_id, [_ref("T1", "/Music/B/song.flac")]
        )
        assert added == 0, "mismo TrackId ya presente → sin duplicado"
        current = service.get_playlist(playlist.playlist_id)
        assert current.track_ids == ("T1",)
        assert current.track_paths == ("/Music/A/song.flac",)

    def test_add_track_references_dedupes_by_path_when_no_track_id(self) -> None:
        port = _CapturePort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist_with_references("Mix", [_ref("", "/a.flac")])
        added = service.add_track_references(
            playlist.playlist_id, [_ref("", "/a.flac"), _ref("T2", "/b.flac")]
        )
        assert added == 1
        current = service.get_playlist(playlist.playlist_id)
        assert current.track_ids == ("", "T2")
        assert current.track_paths == ("/a.flac", "/b.flac")


class TestAlignment:
    def _seeded(self, service: PlaylistService, ids_and_paths):
        playlist = service.create_playlist_with_references(
            "Mix", [_ref(i, p) for i, p in ids_and_paths]
        )
        return playlist

    def test_remove_track_keeps_ids_and_paths_aligned(self) -> None:
        service = PlaylistService(playlists_port=_CapturePort())
        playlist = self._seeded(
            service, [("T1", "/a.flac"), ("T2", "/b.flac"), ("T3", "/c.flac")]
        )
        assert service.remove_track(playlist.playlist_id, 1)
        current = service.get_playlist(playlist.playlist_id)
        assert current.track_ids == ("T1", "T3")
        assert current.track_paths == ("/a.flac", "/c.flac")

    def test_remove_tracks_batch_keeps_alignment(self) -> None:
        service = PlaylistService(playlists_port=_CapturePort())
        playlist = self._seeded(
            service, [("T1", "/a.flac"), ("T2", "/b.flac"), ("T3", "/c.flac")]
        )
        assert service.remove_tracks(playlist.playlist_id, {0, 2})
        current = service.get_playlist(playlist.playlist_id)
        assert current.track_ids == ("T2",)
        assert current.track_paths == ("/b.flac",)

    def test_move_track_keeps_ids_and_paths_aligned(self) -> None:
        service = PlaylistService(playlists_port=_CapturePort())
        playlist = self._seeded(
            service, [("T1", "/a.flac"), ("T2", "/b.flac"), ("T3", "/c.flac")]
        )
        assert service.move_track(playlist.playlist_id, 2, 0)
        current = service.get_playlist(playlist.playlist_id)
        assert current.track_ids == ("T3", "T1", "T2")
        assert current.track_paths == ("/c.flac", "/a.flac", "/b.flac")

    def test_legacy_path_api_aligns_empty_ids(self) -> None:
        """add_track/add_tracks (path-only, seals 10/10) siguen funcionando
        y alinean track_ids vacíos con la misma longitud (nunca skew)."""
        service = PlaylistService(playlists_port=_CapturePort())
        playlist = service.create_playlist("Mix")
        assert service.add_track(playlist.playlist_id, "/a.flac")
        added, already = service.add_tracks(
            playlist.playlist_id, ["/b.flac", "/a.flac"]
        )
        assert (added, already) == (1, 1)
        current = service.get_playlist(playlist.playlist_id)
        assert current.track_paths == ("/a.flac", "/b.flac")
        assert current.track_ids == ("", "")
        assert service.remove_track(playlist.playlist_id, 0)
        assert service.get_playlist(playlist.playlist_id).track_paths == ("/b.flac",)

    def test_v2_loaded_playlist_aligns_on_first_identity_add(self) -> None:
        """Una playlist V2 (paths-only) que recibe su primer TrackId alinea
        los ids legacy como vacíos — remove/move posteriores no rompen."""
        port = _CapturePort(
            [{"id": "p1", "name": "Old", "track_paths": ["/x.flac", "/y.flac"]}]
        )
        service = PlaylistService(playlists_port=port)
        added = service.add_track_references("p1", [_ref("T9", "/z.flac")])
        assert added == 1
        current = service.get_playlist("p1")
        assert current.track_ids == ("", "", "T9")
        assert current.track_paths == ("/x.flac", "/y.flac", "/z.flac")
        assert service.remove_track("p1", 0)
        assert service.get_playlist("p1").track_ids == ("", "T9")
        assert service.get_playlist("p1").track_paths == ("/y.flac", "/z.flac")


class TestV3Persistence:
    def test_v3_roundtrip_restores_track_ids(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist_with_references(
            "Mix", [_ref("T1", "/a.flac"), _ref("T2", "/b.flac")]
        )
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded is not None
        assert reloaded.track_ids == ("T1", "T2"), "ids sobreviven al restart"
        assert reloaded.track_paths == ("/a.flac", "/b.flac")

    def test_v3_preserves_premium_fields(self, tmp_path) -> None:
        """description y appearance (campos premium de main) sobreviven el
        roundtrip V3 junto con la identidad."""
        from michi.domain.playlist import PlaylistHeroMode

        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist_with_references(
            "Mix", [_ref("T1", "/a.flac")]
        )
        service.set_playlist_description(playlist.playlist_id, "Mi mezcla")
        assert service.set_hero_solid(playlist.playlist_id, "#112233")
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded is not None
        assert reloaded.description == "Mi mezcla"
        assert reloaded.appearance.hero_mode == PlaylistHeroMode.SOLID
        assert reloaded.appearance.hero_solid_color == "#112233"
        assert reloaded.track_ids == ("T1",)

    def test_v3_never_downgraded_on_resave(self, tmp_path) -> None:
        """Cargar un V3 con track_ids → mutar (rename) → guardar: el payload
        sigue siendo V3 y conserva LOS MISMOS ids (nunca degrada)."""
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist_with_references(
            "Mix", [_ref("T1", "/a.flac"), _ref("", "/legacy.flac")]
        )
        service.rename_playlist(playlist.playlist_id, "Renamed")
        # El repo productivo guardó de nuevo: inspeccionar el payload crudo.
        raw = repo._load_raw("playlists")
        entry = raw[0]
        assert entry["version"] == 3
        assert entry["tracks"] == [
            {"track_id": "T1", "fallback_path": "/a.flac"},
            {"track_id": "", "fallback_path": "/legacy.flac"},
        ]
        # Reload: la identidad sigue ahí.
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded is not None
        assert reloaded.track_ids == ("T1", "")

    def test_v1_v2_payloads_load_without_writeback(self) -> None:
        """Loader tolerante: V1 y V2 (path-only) cargan con ids vacíos e id
        determinístico — y NO se reescriben durante el load."""
        v1 = {"name": "Old Mix", "track_paths": ["/x.flac"]}
        v2 = {"id": "p2", "name": "Mix2", "track_paths": ["/y.flac"]}
        port = _CapturePort([v1, v2])
        service = PlaylistService(playlists_port=port)
        loaded = service._playlists
        assert len(loaded) == 2
        assert loaded[0].playlist_id == legacy_playlist_id("Old Mix")
        assert loaded[0].track_ids == ()
        assert loaded[1].track_ids == ()
        assert loaded[1].track_paths == ("/y.flac",)
        assert port.raw == [v1, v2], "load nunca escribe"

    def test_v3_external_payload_decodes_with_ids(self) -> None:
        """Un payload V3 externo (emitido por la migración de identidad o un
        R4 histórico) decodifica con track_ids + fallback_paths."""
        raw = {
            "version": 3,
            "id": "p1",
            "name": "Mix",
            "tracks": [
                {"track_id": "T1", "fallback_path": "/a.flac"},
                {"track_id": "", "fallback_path": "/legacy.flac"},
            ],
            "track_paths": ["/a.flac", "/legacy.flac"],
        }
        port = _CapturePort([raw])
        service = PlaylistService(playlists_port=port)
        playlist = service.get_playlist("p1")
        assert playlist is not None
        assert playlist.track_ids == ("T1", "")
        assert playlist.track_paths == ("/a.flac", "/legacy.flac")

    def test_persistence_version_constant_is_3(self) -> None:
        assert PLAYLIST_PERSISTENCE_VERSION == 3, (
            "producción emite V3 — la regresión a V2 degradaba identidad"
        )


class TestLegacyContractsPreserved:
    def test_add_tracks_dedupes(self) -> None:
        service = PlaylistService(playlists_port=_CapturePort())
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        added, already = service.add_tracks(
            playlist.playlist_id, ["/b.flac", "/a.flac", "/b.flac"]
        )
        assert (added, already) == (1, 1)
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/b.flac",
        )

    def test_insert_track_legacy_path_api_keeps_working(self) -> None:
        service = PlaylistService(playlists_port=_CapturePort())
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/a.flac", "/c.flac"])
        assert service.insert_track(playlist.playlist_id, 1, "/b.flac")
        current = service.get_playlist(playlist.playlist_id)
        assert current.track_paths == ("/a.flac", "/b.flac", "/c.flac")
        assert current.track_ids == ("", "", "")

    def test_duplicate_insert_is_noop(self) -> None:
        service = PlaylistService(playlists_port=_CapturePort())
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        before = service._persisted
        assert not service.insert_track(playlist.playlist_id, 0, "/a.flac")
        assert service._persisted == before, "no-op sin escritura durable"
