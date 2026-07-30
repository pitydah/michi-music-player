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


class TestCoverProviderFilepath:
    def test_cover_provider_stores_filepath(self):
        """CoverProviderBridge stores and retrieves last filepath."""
        from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
        cp = CoverProviderBridge()
        cp.set_filepath("/test/path/track.flac")
        assert cp._last_filepath == "/test/path/track.flac"

    def test_request_cover_passes_filepath_to_service(self):
        """_request_from_service passes stored filepath to resolve method."""
        from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
        from unittest.mock import MagicMock
        svc = MagicMock()
        svc.resolve_cover_with_mime.return_value = (None, None)
        cp = CoverProviderBridge(artwork_service=svc)
        cp.set_filepath("/music/test.flac")
        cp._request_from_service("file:test")
        # Verifica que se llamó con el filepath
        args, kwargs = svc.resolve_cover_with_mime.call_args
        assert kwargs.get("filepath") == "/music/test.flac"


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
