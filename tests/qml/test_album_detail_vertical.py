from __future__ import annotations
"""Tests for album detail: model, bridge methods, route params, multi-disc."""

from unittest.mock import MagicMock


class TestAlbumDetailModel:
    def test_model_roles(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        model = AlbumDetailModel()
        names = model.roleNames()
        assert b"trackNumber" in names.values()
        assert b"title" in names.values()
        assert b"artist" in names.values()
        assert b"duration" in names.values()
        assert b"trackId" in names.values()
        assert b"trackUid" in names.values()

    def test_empty_initial_state(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        model = AlbumDetailModel()
        assert model.rowCount() == 0
        assert model.album_title == ""
        assert model.album_artist == ""
        assert model.album_year == 0
        assert model.track_count == 0
        assert model.duration == 0.0

    def test_clear_resets(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        model = AlbumDetailModel()
        model._items = [{"track_id": 1, "title": "Song"}]
        model._album_info = {"title": "Album"}
        model.clear()
        assert model.rowCount() == 0
        assert model.album_title == ""

    def test_load_populates(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        qs = MagicMock()
        qs.fetch_album_detail.return_value = {
            "album_key": "key_1", "title": "Test Album", "artist": "Test Artist",
            "year": 2020, "track_count": 2, "duration": 500.0,
            "tracks": [
                {"track_id": 1, "track_number": 1, "title": "Song A", "artist": "A",
                 "duration": 200.0, "track_uid": "uid1"},
                {"track_id": 2, "track_number": 2, "title": "Song B", "artist": "A",
                 "duration": 300.0, "track_uid": "uid2"},
            ],
        }
        model = AlbumDetailModel()
        model.load("key_1", query_service=qs)
        assert model.rowCount() == 2
        assert model.album_title == "Test Album"
        assert model.album_artist == "Test Artist"
        assert model.album_year == 2020
        assert model.track_count == 2
        assert model.duration == 500.0
        assert model.album_key == "key_1"

    def test_data_access(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        model = AlbumDetailModel()
        model._items = [{"track_id": 1, "track_number": 1, "title": "Song", "artist": "A",
                         "duration": 180.0, "track_uid": "u1"}]
        idx = model.index(0)
        assert model.data(idx, model.TrackNumberRole) == 1
        assert model.data(idx, model.TitleRole) == "Song"
        assert model.data(idx, model.ArtistRole) == "A"
        assert model.data(idx, model.DurationRole) == 180.0
        assert model.data(idx, model.TrackIdRole) == 1
        assert model.data(idx, model.TrackUidRole) == "u1"

    def test_get_track(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        model = AlbumDetailModel()
        model._items = [{"track_id": 1, "title": "Song"}]
        t = model.get_track(0)
        assert t is not None
        assert t["track_id"] == 1

    def test_get_track_out_of_range(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        model = AlbumDetailModel()
        assert model.get_track(0) is None
        assert model.get_track(-1) is None

    def test_multi_disc_tracks(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        qs = MagicMock()
        qs.fetch_album_detail.return_value = {
            "album_key": "key_disc", "title": "Multi-Disc", "artist": "Artist",
            "year": 2021, "track_count": 4, "duration": 1000.0,
            "tracks": [
                {"track_id": 1, "track_number": 1, "title": "D1T1", "artist": "A",
                 "duration": 200.0, "track_uid": "u1"},
                {"track_id": 2, "track_number": 1, "title": "D2T1", "artist": "A",
                 "duration": 300.0, "track_uid": "u2"},
                {"track_id": 3, "track_number": 2, "title": "D1T2", "artist": "A",
                 "duration": 250.0, "track_uid": "u3"},
                {"track_id": 4, "track_number": 2, "title": "D2T2", "artist": "A",
                 "duration": 250.0, "track_uid": "u4"},
            ],
        }
        model = AlbumDetailModel()
        model.load("key_disc", query_service=qs)
        assert model.rowCount() == 4
        assert model.track_count == 4

    def test_missing_tracks(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        qs = MagicMock()
        qs.fetch_album_detail.return_value = None
        model = AlbumDetailModel()
        model.load("missing", query_service=qs)
        assert model.rowCount() == 0

    def test_cover_key_fallback(self):
        from ui_qml.models.AlbumDetailModel import AlbumDetailModel
        model = AlbumDetailModel()
        model._album_info = {"album_key": "key1"}
        assert model.cover_key == "key1"


class TestAlbumDetailBridge:
    def test_get_album_detail(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_album_detail.return_value = {
            "album_key": "key_1", "title": "Test", "artist": "A",
            "year": 2020, "track_count": 3, "duration": 600.0,
            "tracks": [{"track_id": 1, "title": "Song", "track_number": 1}],
        }
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getAlbumDetail("key_1")
        assert result.get("ok") is True
        assert result["album_key"] == "key_1"

    def test_get_album_detail_not_found(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_album_detail.return_value = None
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getAlbumDetail("nonexistent")
        assert result.get("ok") is False
        assert result.get("error") == "NOT_FOUND"

    def test_get_album_detail_no_qs(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        result = bridge.getAlbumDetail("key")
        assert result.get("ok") is False
        assert result.get("error") == "NO_QUERY_SERVICE"

    def test_get_album_tracks(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_album_tracks_internal.return_value = [
            {"track_id": 1, "filepath": "/m/a.flac", "title": "A", "artist": "X",
             "duration": 200.0, "track_number": 1, "track_uid": "u1"},
        ]
        bridge = LibraryBridge(query_service=qs)
        tracks = bridge.getAlbumTracks("key")
        assert len(tracks) == 1
        assert tracks[0]["title"] == "A"
        assert "filepath" not in tracks[0]

    def test_play_album(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_album_tracks_internal.return_value = [
            {"filepath": "/m/a.flac", "title": "A"},
            {"filepath": "/m/b.flac", "title": "B"},
        ]
        class FakePlayer:
            def enqueue(self, paths, play_now=False):
                self.enqueued = list(paths)
        player = FakePlayer()
        bridge = LibraryBridge(query_service=qs, playback_ctrl=player)
        result = bridge.playAlbum("key")
        assert result.get("ok") is True
        assert result.get("count") == 2

    def test_play_album_no_qs(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        result = bridge.playAlbum("key")
        assert result.get("ok") is False
        assert result.get("error") == "NO_QUERY_SERVICE"

    def test_play_album_no_tracks(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_album_tracks_internal.return_value = []
        bridge = LibraryBridge(query_service=qs, playback_ctrl=MagicMock())
        result = bridge.playAlbum("key")
        assert result.get("ok") is False
        assert result.get("error") == "NO_TRACKS"

    def test_enqueue_album(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_album_tracks_internal.return_value = [
            {"filepath": "/m/a.flac"},
            {"filepath": "/m/b.flac"},
        ]
        class FakePlayer:
            def enqueue(self, paths, play_now=False):
                self.enqueued = list(paths)
        player = FakePlayer()
        bridge = LibraryBridge(query_service=qs, playback_ctrl=player)
        result = bridge.enqueueAlbum("key")
        assert result.get("ok") is True
        assert result.get("count") == 2


class TestAlbumDetailRouteParams:
    def test_album_detail_route_has_params(self):
        from ui_qml_bridge.route_registry import ROUTES
        info = ROUTES.get("album_detail")
        assert info is not None
        assert "params" in info
        assert "album_key" in info["params"]
        assert info["params"]["album_key"]["required"] is True

    def test_album_detail_missing_required_blocked(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigateWithParams("album_detail", {})
        assert bridge.currentRoute != "album_detail"

    def test_album_detail_with_key_navigates(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigateWithParams("album_detail", {"album_key": "key_1"})
        assert bridge.currentRoute == "album_detail"
        assert bridge.currentParams.get("album_key") == "key_1"

    def test_route_registry_bridge_exposes_params(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        bridge = RouteRegistryBridge()
        params = bridge.getParams("album_detail")
        assert "album_key" in params
        required = bridge.getRequiredParamKeys("album_detail")
        assert "album_key" in required

    def test_has_required_params(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        bridge = RouteRegistryBridge()
        assert bridge.hasRequiredParams("album_detail", {"album_key": "k"}) is True
        assert bridge.hasRequiredParams("album_detail", {}) is False

    def test_route_status_functional(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert ROUTES["album_detail"]["status"] == "functional"
