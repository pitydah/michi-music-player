"""Tests for artist detail: model, bridge methods, route params, unknown artist."""
from __future__ import annotations

from unittest.mock import MagicMock


class TestArtistListModel:
    def test_artist_model_roles(self):
        from ui_qml.models.ArtistListModel import ArtistListModel
        model = ArtistListModel()
        names = model.roleNames()
        assert b"name" in names.values()
        assert b"trackCount" in names.values()
        assert b"albumCount" in names.values()

    def test_artist_model_data_access(self):
        from ui_qml.models.ArtistListModel import ArtistListModel
        model = ArtistListModel()
        model._items = [{"name": "Artist A", "track_count": 10, "album_count": 2, "cover_key": "c1"}]
        idx = model.index(0)
        assert model.data(idx, model.NameRole) == "Artist A"
        assert model.data(idx, model.TrackCountRole) == 10
        assert model.data(idx, model.AlbumCountRole) == 2

    def test_artist_model_refresh(self):
        from ui_qml.models.ArtistListModel import ArtistListModel
        qs = MagicMock()
        qs.count_artists.return_value = 3
        qs.fetch_artists.return_value = [
            {"name": "A1", "track_count": 5, "album_count": 1, "cover_key": "k1"},
            {"name": "A2", "track_count": 10, "album_count": 2, "cover_key": "k2"},
            {"name": "A3", "track_count": 15, "album_count": 3, "cover_key": "k3"},
        ]
        model = ArtistListModel(query_service=qs)
        model.refresh()
        assert model.totalCount == 3
        assert model.count == 3
        assert model.data(model.index(0), model.NameRole) == "A1"

    def test_artist_model_search(self):
        from ui_qml.models.ArtistListModel import ArtistListModel
        qs = MagicMock()
        qs.count_artists.return_value = 1
        qs.fetch_artists.return_value = [{"name": "Match", "track_count": 3, "album_count": 1, "cover_key": "k"}]
        model = ArtistListModel(query_service=qs)
        model.refresh(search="Match")
        assert model.totalCount == 1
        assert model.count == 1


class TestArtistDetailBridge:
    def test_get_artist_detail(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = {
            "artist": "Test Artist", "track_count": 10, "album_count": 2,
            "tracks": [{"track_id": 1, "title": "Song", "duration": 200.0}],
        }
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getArtistDetail("Test Artist")
        assert result.get("ok") is True
        assert result["artist"] == "Test Artist"
        assert result["track_count"] == 10

    def test_get_artist_detail_no_qs(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        result = bridge.getArtistDetail("Artist")
        assert result.get("ok") is False

    def test_get_artist_detail_not_found(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = None
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getArtistDetail("Unknown")
        assert result.get("ok") is False

    def test_get_artist_tracks(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_artist_tracks_internal.return_value = [
            {"track_id": 1, "filepath": "/m/a.flac", "title": "A", "album": "Al",
             "duration": 200.0, "track_number": 1, "track_uid": "u1"},
        ]
        bridge = LibraryBridge(query_service=qs)
        tracks = bridge.getArtistTracks("Artist")
        assert len(tracks) == 1
        assert tracks[0]["title"] == "A"

    def test_get_artist_albums(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_artist_tracks_internal.return_value = [
            {"album_key": "k1", "album": "Album 1"},
            {"album_key": "k2", "album": "Album 2"},
            {"album_key": "k1", "album": "Album 1"},
        ]
        bridge = LibraryBridge(query_service=qs)
        albums = bridge.getArtistAlbums("Artist")
        assert len(albums) == 2
        keys = [a["album_key"] for a in albums]
        assert "k1" in keys
        assert "k2" in keys

    def test_play_artist(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_artist_tracks_internal.return_value = [
            {"filepath": "/m/a.flac"}, {"filepath": "/m/b.flac"},
        ]
        class FakePlayer:
            def enqueue(self, paths, play_now=False):
                self.enqueued = list(paths)
        player = FakePlayer()
        bridge = LibraryBridge(query_service=qs, playback_ctrl=player)
        result = bridge.playArtist("Artist")
        assert result.get("ok") is True
        assert result.get("count") == 2

    def test_play_artist_no_tracks(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = MagicMock()
        qs.fetch_artist_tracks_internal.return_value = []
        bridge = LibraryBridge(query_service=qs, playback_ctrl=MagicMock())
        result = bridge.playArtist("Artist")
        assert result.get("ok") is False

    def test_play_artist_no_qs(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        result = bridge.playArtist("Artist")
        assert result.get("ok") is False


class TestUnknownArtist:
    def test_missing_artist_can_be_filtered(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [5]
        db.conn.execute.return_value.fetchall.return_value = []
        qs = LibraryQueryService(db=db)
        count = qs.count_tracks(missing_artist=True)
        assert count == 5

    def test_album_artist_normalization(self):
        from ui_qml_bridge.library_query_service import _artist_key_sql
        sql = _artist_key_sql()
        assert "albumartist" in sql
        assert "artist" in sql

    def test_artist_with_only_albumartist(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [1]
        db.conn.execute.return_value.fetchall.return_value = [
            ("AlbumArtist", 10, 2, 3600.0),
        ]
        qs = LibraryQueryService(db=db)
        artists = qs.fetch_artists(offset=0, limit=10)
        assert len(artists) == 1
        assert artists[0]["name"] == "AlbumArtist"


class TestArtistDetailRouteParams:
    def test_artist_detail_route_has_params(self):
        from ui_qml_bridge.route_registry import ROUTES
        info = ROUTES.get("artist_detail")
        assert info is not None
        assert "params" in info
        assert "artist" in info["params"]
        assert info["params"]["artist"]["required"] is True

    def test_artist_detail_with_param_navigates(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigateWithParams("artist_detail", {"artist": "Test Artist"})
        assert bridge.currentRoute == "artist_detail"
        assert bridge.currentParams.get("artist") == "Test Artist"

    def test_artist_detail_missing_required_blocked(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigateWithParams("artist_detail", {})
        assert bridge.currentRoute != "artist_detail"

    def test_route_status_functional(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert ROUTES["artist_detail"]["status"] == "functional"


class TestLibraryQueryServiceArtistMethods:
    def test_artist_tracks_internal(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = []
        db.conn.execute.return_value.fetchone.return_value = [0]
        qs = LibraryQueryService(db=db)
        tracks = qs.fetch_artist_tracks_internal("Artist")
        assert tracks == []

    def test_artist_detail(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [0]
        db.conn.execute.return_value.fetchall.return_value = [
            (1, "/f.flac", "T", "Al", 200.0, 1, "u1", "ak"),
        ]
        qs = LibraryQueryService(db=db)
        detail = qs.fetch_artist_detail("Artist")
        assert detail is not None
        assert detail["artist"] == "Artist"
        assert "filepath" not in str(detail.get("tracks", [{}])[0])
