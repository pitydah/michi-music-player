"""Test full metadata pipeline: extraction → normalization → persistence → display."""
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine


PNG_COVER = b"\x89PNG\r\n\x1a\nreal-cover"
JPEG_COVER = b"\xff\xd8\xffreal-cover"


class _CoverBridgeStub(QObject):
    coverReady = Signal(str, str)
    coverInvalidated = Signal(str)

    @Slot(str, int, result=str)
    def requestCover(self, _cover_key: str, _requested_size: int) -> str:
        return ""


def _write_mp3_with_cover(path: Path, cover: bytes = PNG_COVER) -> None:
    from mutagen.id3 import APIC, ID3

    path.write_bytes((b"\xff\xfb\x90\x64" + b"\x00" * 413) * 3)
    tags = ID3()
    tags.add(APIC(mime="image/png", type=3, desc="Cover", data=cover))
    tags.save(path)


def _write_flac_with_cover(path: Path, cover: bytes = JPEG_COVER) -> None:
    import numpy as np
    import soundfile as sf
    from mutagen.flac import FLAC, Picture

    sf.write(path, np.zeros(64, dtype=np.float32), 8000, format="FLAC")
    audio = FLAC(path)
    picture = Picture()
    picture.type = 3
    picture.mime = "image/jpeg"
    picture.data = cover
    audio.add_picture(picture)
    audio.save()


class TestPlayerServicePipeline:
    def test_player_service_stores_filepath(self):
        """play(filepath) makes filepath available via property."""
        from audio.player_service import PlayerService
        ps = PlayerService()
        with patch.object(ps, '_engine'), patch.object(ps, '_hybrid'):
            ps.play("/test/path/track.flac", title="Test", artist="Artist")
            assert ps.current_filepath == "/test/path/track.flac"

    def test_track_context_contains_filepath(self):
        """trackContextChanged signal emits dict with filepath."""
        from audio.player_service import PlayerService
        ps = PlayerService()
        received = []
        def handler(ctx): received.append(ctx)
        ps.trackContextChanged.connect(handler)
        with patch.object(ps, '_engine'), patch.object(ps, '_hybrid'):
            ps.play("/test/path/track.flac", "Test", "Artist", "Album")
        assert len(received) > 0
        ctx = received[0]
        assert ctx.get("filepath") == "/test/path/track.flac"
        assert ctx.get("title") == "Test"
        assert ctx.get("artist") == "Artist"
        assert ctx.get("album") == "Album"

    def test_track_context_uses_library_metadata_and_namespaced_album_cover(self):
        """Library metadata completes the playback DTO and album cover key."""
        from audio.player_service import PlayerService

        db = MagicMock()
        db.fetch_track_context.return_value = {
            "title": "Library title",
            "artist": "Library artist",
            "album": "Library album",
            "album_key": "album-123",
            "track_uid": "track-456",
            "year": 2024,
            "genre": "Jazz",
            "duration": 241.5,
            "format": "flac",
            "sample_rate": 96000,
            "bit_depth": 24,
            "bitrate": 2300,
        }
        service = PlayerService(library_db=db)
        received = []
        service.trackContextChanged.connect(received.append)

        with patch.object(service, "_engine"), patch.object(service, "_hybrid"):
            service.play("/music/track.flac")
            service._emitTrackContext()

        assert received[-1] == {
            "filepath": "/music/track.flac",
            "title": "Library title",
            "artist": "Library artist",
            "album": "Library album",
            "album_key": "album-123",
            "track_uid": "track-456",
            "cover_key": "album:album-123",
            "year": 2024,
            "genre": "Jazz",
            "duration": 241.5,
            "format": "flac",
            "sample_rate": 96000,
            "bit_depth": 24,
            "bitrate": 2300,
        }

    def test_track_context_uses_track_namespace_without_album(self):
        """A track UID remains resolvable when the library has no album key."""
        from audio.player_service import PlayerService

        db = MagicMock()
        db.fetch_track_context.return_value = {
            "title": "Single",
            "artist": "Artist",
            "album": "",
            "album_key": "",
            "track_uid": "track-789",
            "year": 0,
            "genre": "",
            "duration": 180.0,
            "format": "mp3",
            "sample_rate": 44100,
            "bit_depth": 16,
            "bitrate": 320,
        }
        service = PlayerService(library_db=db)
        received = []
        service.trackContextChanged.connect(received.append)

        service._emitTrackContext(filepath="/music/single.mp3")

        assert received[-1]["album_key"] == ""
        assert received[-1]["cover_key"] == "track:track-789"


class TestCoverArtServiceResolution:
    def test_extracts_real_embedded_cover_from_mp3_and_flac(self, tmp_path):
        """Mutagen extracts actual APIC and FLAC picture blocks."""
        from core.library.artwork_resolver import CoverArtService

        mp3_path = tmp_path / "embedded.mp3"
        flac_path = tmp_path / "embedded.flac"
        _write_mp3_with_cover(mp3_path)
        _write_flac_with_cover(flac_path)

        service = CoverArtService()

        assert service.resolve_cover_with_mime(f"file:{mp3_path}") == (
            "image/png",
            PNG_COVER,
        )
        assert service.resolve_cover_with_mime(f"file:{flac_path}") == (
            "image/jpeg",
            JPEG_COVER,
        )

    def test_resolve_with_album_key(self):
        """resolve_cover_with_mime returns cached cover for album key."""
        from core.library.artwork_resolver import CoverArtService
        db = MagicMock()
        db.get_album_art_cache.return_value = ("image/jpeg", b"fake_image_data")
        svc = CoverArtService(db=db)
        mime, data = svc.resolve_cover_with_mime("some_album_key")
        assert mime == "image/jpeg"
        assert data == b"fake_image_data"

    def test_resolve_with_album_prefix_key(self):
        """resolve_cover_with_mime strips 'album:' prefix and looks up."""
        from core.library.artwork_resolver import CoverArtService
        db = MagicMock()
        db.get_album_art_cache.return_value = ("image/png", b"prefix_data")
        svc = CoverArtService(db=db)
        mime, data = svc.resolve_cover_with_mime("album:real_key")
        assert data == b"prefix_data"

    def test_resolve_with_filepath_embedded(self):
        """resolve_cover_with_mime tries embedded cover from filepath."""
        from core.library.artwork_resolver import CoverArtService
        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(b"ID3")
        tmp.close()
        svc = CoverArtService(db=None)
        mime, data = svc.resolve_cover_with_mime("file:" + tmp.name)
        os.unlink(tmp.name)
        # Should not crash, may or may not find embedded cover
        assert mime is None or isinstance(mime, str)

    def test_resolve_with_filepath_sidecar(self):
        """resolve_cover_with_mime tries sidecar in same directory."""
        from core.library.artwork_resolver import CoverArtService
        import tempfile
        import os
        tmpdir = tempfile.mkdtemp()
        # Create audio file
        audio_path = os.path.join(tmpdir, "track.flac")
        open(audio_path, "w").close()
        # Create sidecar cover
        cover_path = os.path.join(tmpdir, "cover.jpg")
        with open(cover_path, "wb") as f:
            f.write(b"fake_jpeg_data")
        svc = CoverArtService(db=None)
        mime, data = svc.resolve_cover_with_mime("file:" + audio_path)
        assert data == b"fake_jpeg_data"
        os.unlink(audio_path)
        os.unlink(cover_path)
        os.rmdir(tmpdir)

    def test_png_signature_overrides_incorrect_cached_mime(self):
        """PNG bytes are never exposed as image/jpeg."""
        from core.library.artwork_resolver import CoverArtService

        png_data = b"\x89PNG\r\n\x1a\n" + b"payload"
        db = MagicMock()
        db.get_album_art_cache.return_value = ("image/jpeg", png_data)

        mime, data = CoverArtService(db=db).resolve_cover_with_mime("album:key")

        assert mime == "image/png"
        assert data == png_data

    def test_sidecar_search_is_case_insensitive_and_prioritized(self, tmp_path):
        """cover.* wins deterministically over folder.* regardless of casing."""
        from core.library.artwork_resolver import CoverArtService

        track = tmp_path / "track.flac"
        track.write_bytes(b"audio")
        (tmp_path / "FOLDER.PNG").write_bytes(b"\x89PNG\r\n\x1a\nfolder")
        preferred = b"\xff\xd8\xffcover"
        (tmp_path / "Cover.JPG").write_bytes(preferred)

        mime, data = CoverArtService().resolve_cover_with_mime(f"file:{track}")

        assert mime == "image/jpeg"
        assert data == preferred

    def test_oversized_sidecar_is_rejected(self, tmp_path, caplog):
        """Artwork larger than 10 MiB is rejected with a logged reason."""
        from core.library.artwork_resolver import CoverArtService, MAX_COVER_BYTES

        track = tmp_path / "track.flac"
        track.write_bytes(b"audio")
        (tmp_path / "cover.jpg").write_bytes(b"x" * (MAX_COVER_BYTES + 1))

        mime, data = CoverArtService().resolve_cover_with_mime(f"file:{track}")

        assert (mime, data) == (None, None)
        assert "oversized cover" in caplog.text.lower()

    def test_track_key_uses_album_cache_then_track_filepath(self, tmp_path):
        """track: resolves album art first and embedded/sidecar art second."""
        from core.library.artwork_resolver import CoverArtService

        track = tmp_path / "track.flac"
        track.write_bytes(b"audio")
        sidecar = b"\x89PNG\r\n\x1a\nsidecar"
        (tmp_path / "front.png").write_bytes(sidecar)
        db = MagicMock()
        db.get_album_art_cache.return_value = None
        db.conn.execute.return_value.fetchone.return_value = ("missing-album", str(track))

        mime, data = CoverArtService(db=db).resolve_cover_with_mime("track:uid-1")

        assert mime == "image/png"
        assert data == sidecar

    def test_backfills_missing_album_art_and_reports_counts(self, tmp_path):
        """Backfill reviews missing albums, recovers embedded art, and skips misses."""
        from core.library.artwork_resolver import CoverArtService

        recovered_track = tmp_path / "recovered.mp3"
        skipped_track = tmp_path / "skipped.mp3"
        _write_mp3_with_cover(recovered_track)
        skipped_track.write_bytes((b"\xff\xfb\x90\x64" + b"\x00" * 413) * 3)
        connection = sqlite3.connect(":memory:")
        connection.execute(
            "CREATE TABLE media_items ("
            "album_key TEXT, filepath TEXT, deleted_at REAL)"
        )
        connection.execute(
            "CREATE TABLE album_art_cache ("
            "album_hash TEXT PRIMARY KEY, mime TEXT, data BLOB)"
        )
        connection.executemany(
            "INSERT INTO media_items (album_key, filepath, deleted_at) VALUES (?, ?, NULL)",
            [
                ("album-recovered", str(recovered_track)),
                ("album-skipped", str(skipped_track)),
                ("album-cached", str(recovered_track)),
            ],
        )
        connection.execute(
            "INSERT INTO album_art_cache (album_hash, mime, data) VALUES (?, ?, ?)",
            ("album-cached", "image/jpeg", JPEG_COVER),
        )
        service = CoverArtService(db=SimpleNamespace(conn=connection))

        counts = service.backfill_missing_album_art()

        assert counts == {
            "reviewed": 2,
            "recovered": 1,
            "failed": 0,
            "skipped": 1,
            "recovered_keys": ["album-recovered"],
        }
        cached = connection.execute(
            "SELECT mime, data FROM album_art_cache WHERE album_hash = ?",
            ("album-recovered",),
        ).fetchone()
        assert cached == ("image/png", PNG_COVER)

    def test_backfill_reports_failed_cache_write(self, tmp_path):
        """An extracted cover with an unsuccessful cache write is reported as failed."""
        from core.library.artwork_resolver import CoverArtService

        track = tmp_path / "uncacheable.mp3"
        _write_mp3_with_cover(track)
        connection = sqlite3.connect(":memory:")
        connection.execute(
            "CREATE TABLE media_items ("
            "album_key TEXT, filepath TEXT, deleted_at REAL)"
        )
        connection.execute(
            "CREATE TABLE album_art_cache ("
            "album_hash TEXT PRIMARY KEY, mime TEXT, data BLOB)"
        )
        connection.execute(
            "CREATE TRIGGER reject_album_art BEFORE INSERT ON album_art_cache "
            "BEGIN SELECT RAISE(FAIL, 'blocked'); END"
        )
        connection.execute(
            "INSERT INTO media_items (album_key, filepath, deleted_at) VALUES (?, ?, NULL)",
            ("album-failed", str(track)),
        )

        counts = CoverArtService(
            db=SimpleNamespace(conn=connection)
        ).backfill_missing_album_art()

        assert counts == {
            "reviewed": 1,
            "recovered": 0,
            "failed": 1,
            "skipped": 0,
            "recovered_keys": [],
        }

    def test_backfill_recovers_sidecar_cover_when_no_embedded(self, tmp_path):
        """Backfill falls back to sidecar images and reports recovered keys."""
        from core.library.artwork_resolver import CoverArtService

        track = tmp_path / "track.flac"
        track.write_bytes(b"audio")
        sidecar = tmp_path / "cover.jpg"
        sidecar.write_bytes(JPEG_COVER)
        connection = sqlite3.connect(":memory:")
        connection.execute(
            "CREATE TABLE media_items ("
            "album_key TEXT, filepath TEXT, deleted_at REAL)"
        )
        connection.execute(
            "CREATE TABLE album_art_cache ("
            "album_hash TEXT PRIMARY KEY, mime TEXT, data BLOB)"
        )
        connection.execute(
            "INSERT INTO media_items (album_key, filepath, deleted_at) VALUES (?, ?, NULL)",
            ("album-sidecar", str(track)),
        )
        service = CoverArtService(db=SimpleNamespace(conn=connection))

        counts = service.backfill_missing_album_art()

        assert counts == {
            "reviewed": 1,
            "recovered": 1,
            "failed": 0,
            "skipped": 0,
            "recovered_keys": ["album-sidecar"],
        }
        cached = connection.execute(
            "SELECT mime, data FROM album_art_cache WHERE album_hash = ?",
            ("album-sidecar",),
        ).fetchone()
        assert cached == ("image/jpeg", JPEG_COVER)


class TestCoverProviderKeyResolution:
    def test_request_cover_uses_only_the_requested_key(self):
        """Cover requests cannot inherit a filepath from another track."""
        from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge

        svc = MagicMock()
        svc.resolve_cover_with_mime.return_value = (None, None)
        cp = CoverProviderBridge(artwork_service=svc)

        cp._request_from_service("track:uid-1")

        svc.resolve_cover_with_mime.assert_called_once_with("track:uid-1")
        assert not hasattr(cp, "_last_filepath")

    def test_invalidate_cover_clears_all_references_and_emits_signal(self):
        """Single-key invalidation removes value, expiry, and thumbnail references."""
        from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge

        service = MagicMock()
        service.resolve_cover_with_mime.return_value = ("image/png", PNG_COVER)
        bridge = CoverProviderBridge(artwork_service=service)
        invalidated = []
        bridge.coverInvalidated.connect(invalidated.append)
        bridge.requestCover("album:one", 256)

        result = bridge.invalidateCover("album:one")

        assert result == {"ok": True, "removed": True}
        assert bridge.isCached("album:one") is False
        assert "album:one" not in bridge._cache_expiry
        assert "album:one" not in bridge._thumbnail_references
        assert invalidated == ["album:one"]

    def test_invalidate_many_deduplicates_keys_and_rejects_invalid_json(self):
        """Batch invalidation accepts a JSON list and reports malformed input."""
        from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge

        service = MagicMock()
        service.resolve_cover_with_mime.return_value = ("image/jpeg", JPEG_COVER)
        bridge = CoverProviderBridge(artwork_service=service)
        invalidated = []
        bridge.coverInvalidated.connect(invalidated.append)
        bridge.requestCover("album:one", 128)
        bridge.requestCover("album:two", 128)

        result = bridge.invalidateMany(json.dumps(["album:one", "album:two", "album:one", ""]))

        assert result == {"ok": True, "invalidated": 2, "removed": 2}
        assert invalidated == ["album:one", "album:two"]
        assert bridge.cacheSize == 0
        assert bridge.invalidateMany("not-json") == {
            "ok": False,
            "invalidated": 0,
            "removed": 0,
            "error": "invalid_json",
        }

    def test_lru_eviction_clears_thumbnail_reference(self):
        """Evicting an LRU entry cannot leave a stale thumbnail reference."""
        from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge

        service = MagicMock()
        service.resolve_cover_with_mime.return_value = ("image/jpeg", JPEG_COVER)
        bridge = CoverProviderBridge(artwork_service=service)
        bridge._max_cache = 1

        bridge.requestCover("album:old", 64)
        bridge.requestCover("album:new", 128)

        assert "album:old" not in bridge._thumbnail_references
        assert "album:new" in bridge._thumbnail_references


class TestCoverImageContract:
    def test_semantic_state_initials_and_stale_ready_guard(self, qapp):
        """CoverImage exposes semantic state and ignores stale cover results."""
        bridge = _CoverBridgeStub()
        engine = QQmlEngine()
        engine.rootContext().setContextProperty("coverProviderBridge", bridge)
        component = QQmlComponent(engine)
        component.loadUrl(
            QUrl.fromLocalFile(
                str(Path(__file__).parents[1] / "ui_qml/components/CoverImage.qml")
            )
        )
        assert component.isReady(), [str(error) for error in component.errors()]
        cover = component.create()
        assert cover is not None
        cover.setProperty("fallbackTitle", "Dark Side")
        cover.setProperty("coverKey", "album:current")
        qapp.processEvents()

        assert cover.property("artworkState") == "missing"
        assert cover.property("placeholderText") == "DS"
        assert cover.property("accessibleLabel") == "Dark Side"
        bridge.coverReady.emit("album:stale", "data:image/png;base64,c3RhbGU=")
        assert cover.property("coverUrl") == ""
        bridge.coverReady.emit("album:current", "data:image/png;base64,Y3VycmVudA==")
        assert cover.property("coverUrl") == "data:image/png;base64,Y3VycmVudA=="
        bridge.coverInvalidated.emit("album:current")
        qapp.processEvents()
        assert cover.property("coverUrl") == ""

    def test_cover_change_clears_url_and_reduced_motion_disables_fade(self, qapp):
        """Changing identity clears stale artwork and reduced motion removes fade time."""
        bridge = _CoverBridgeStub()
        engine = QQmlEngine()
        engine.rootContext().setContextProperty("coverProviderBridge", bridge)
        component = QQmlComponent(
            engine,
            QUrl.fromLocalFile(
                str(Path(__file__).parents[1] / "ui_qml/components/CoverImage.qml")
            ),
        )
        assert component.isReady(), [str(error) for error in component.errors()]
        cover = component.create()
        assert cover is not None
        cover.setProperty("coverUrl", "data:image/png;base64,b2xk")
        cover.setProperty("reducedMotion", True)

        cover.setProperty("coverKey", "album:new")
        qapp.processEvents()

        assert cover.property("coverUrl") == ""
        assert cover.property("fadeDuration") == 0


class TestNowPlayingBridgeContext:
    def test_cover_key_from_context(self):
        """NowPlayingBridge coverPath comes from context dict."""
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        bridge = NowPlayingBridge(player_service=MagicMock(), queue_service=MagicMock())
        context = {
            "filepath": "/test/album/track.flac",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "cover_key": "album:test_hash",
            "year": 2024,
        }
        bridge._on_track_context(context)
        assert bridge.coverPath == "album:test_hash"

    def test_cover_key_falls_back_to_album_then_track_namespace(self):
        """Context fallback uses stable album and track namespaces."""
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

        bridge = NowPlayingBridge(player_service=MagicMock(), queue_service=MagicMock())
        bridge._on_track_context({"album_key": "album-1", "track_uid": "track-1"})
        assert bridge.coverPath == "album:album-1"

        bridge._on_track_context({"track_uid": "track-2"})
        assert bridge.coverPath == "track:track-2"

    @staticmethod
    def _bridge_with_clean_player():
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

        player = MagicMock()
        player.current = ""
        player.current_filepath = ""
        player.current_path = ""
        player.state = "stopped"
        player.duration = 0
        return NowPlayingBridge(player_service=player, queue_service=MagicMock())

    def test_on_track_context_updates_all_state_from_context(self):
        """trackContextChanged is the single source for track and quality state."""
        bridge = self._bridge_with_clean_player()
        context = {
            "filepath": "/music/track.flac",
            "title": "Ctx Title",
            "artist": "Ctx Artist",
            "album": "Ctx Album",
            "album_key": "album-ctx",
            "track_uid": "uid-ctx",
            "cover_key": "album:album-ctx",
            "duration": 241.0,
            "format": "flac",
            "sample_rate": 96000,
            "bit_depth": 24,
            "bitrate": 2300,
        }
        bridge._on_track_context(context)

        assert bridge.trackTitle == "Ctx Title"
        assert bridge.trackArtist == "Ctx Artist"
        assert bridge.trackAlbum == "Ctx Album"
        assert bridge.coverKey == "album:album-ctx"
        assert bridge.coverPath == "album:album-ctx"
        assert bridge.duration == 241
        assert bridge.formatLabel == "flac"
        assert bridge.sampleRate == "96000"
        assert bridge.bitDepth == "24"
        assert bridge.bitrate == "2300"
        assert bridge.sourceType == "local_file"
        assert bridge.qualityInfoAvailable is True

    def test_coverKey_is_primary_property_and_coverPath_is_alias(self):
        """coverKey exposes the namespaced key; coverPath mirrors it."""
        from PySide6.QtCore import QObject

        meta = QObject.staticMetaObject  # sanity check that bridge is a QObject
        assert meta is not None
        bridge = self._bridge_with_clean_player()
        bridge._on_track_context({"filepath": "/a/b.flac", "cover_key": "album:xyz"})
        assert bridge.coverKey == "album:xyz"
        assert bridge.coverPath == bridge.coverKey

    def test_history_is_enriched_from_context_after_track_event(self):
        """A track_changed entry is enriched with canonical context fields."""
        bridge = self._bridge_with_clean_player()
        bridge._on_track("Song", "Artist", "Album")
        # The 2-string event produces a path-namespaced cover key.
        assert bridge.history[0]["cover_key"] != "album:canonical"

        bridge._on_track_context({
            "filepath": "/music/song.flac",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "album_key": "canonical",
            "track_uid": "uid-1",
            "cover_key": "album:canonical",
            "duration": 200,
            "source_type": "local_file",
        })

        entry = bridge.history[0]
        assert entry["title"] == "Song"
        assert entry["cover_key"] == "album:canonical"
        assert entry["track_uid"] == "uid-1"
        assert entry["duration"] == 200
        assert entry["source_type"] == "local_file"
        # No duplicate entry is created when context matches the last track.
        assert len(bridge.history) == 1

    def test_history_is_inserted_from_context_without_track_event(self):
        """Context alone seeds a canonical history entry."""
        bridge = self._bridge_with_clean_player()
        bridge._on_track_context({
            "filepath": "/music/ctx.flac",
            "title": "Ctx Song",
            "artist": "Ctx Artist",
            "album": "Ctx Album",
            "album_key": "ctx-album",
            "track_uid": "ctx-uid",
            "cover_key": "album:ctx-album",
            "duration": 99,
            "source_type": "local_file",
        })

        assert len(bridge.history) == 1
        entry = bridge.history[0]
        assert entry["title"] == "Ctx Song"
        assert entry["cover_key"] == "album:ctx-album"
        assert entry["track_uid"] == "ctx-uid"
        assert entry["duration"] == 99
        assert entry["source_type"] == "local_file"
