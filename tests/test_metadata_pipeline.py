"""Test full metadata pipeline: extraction → normalization → persistence → display."""
from unittest.mock import MagicMock, patch


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
        db.conn.execute.return_value.fetchone.return_value = (
            "Library title",
            "Library artist",
            "Library album",
            "album-123",
            "track-456",
            2024,
            "Jazz",
            241.5,
            "flac",
            96000,
            24,
            2300,
        )
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
        db.conn.execute.return_value.fetchone.return_value = (
            "Single",
            "Artist",
            "",
            "",
            "track-789",
            0,
            "",
            180.0,
            "mp3",
            44100,
            16,
            320,
        )
        service = PlayerService(library_db=db)
        received = []
        service.trackContextChanged.connect(received.append)

        service._emitTrackContext(filepath="/music/single.mp3")

        assert received[-1]["album_key"] == ""
        assert received[-1]["cover_key"] == "track:track-789"


class TestCoverArtServiceResolution:
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
