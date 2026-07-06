"""E2E: verify all Wave IX bridges, models, and services import and respond correctly."""
from __future__ import annotations

from unittest.mock import MagicMock


class TestWave9CoreBridges:
    def test_context_bindings_loaded(self):
        from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
        assert len(QML_CONTEXT_BINDINGS) >= 35
        assert "libraryBridge" in QML_CONTEXT_BINDINGS
        assert "queueBridge" in QML_CONTEXT_BINDINGS
        assert "historyBridge" in QML_CONTEXT_BINDINGS
        assert "actionRegistry" in QML_CONTEXT_BINDINGS
        assert "globalSearchBridge" in QML_CONTEXT_BINDINGS
        assert "jobBridge" in QML_CONTEXT_BINDINGS
        assert "homeBridge" in QML_CONTEXT_BINDINGS

    def test_factory_creates_all_bridges(self):
        from ui_qml_bridge.bridge_factory import BridgeFactory
        from ui_qml_bridge.service_bundle import ServiceBundle
        svc = ServiceBundle()
        factory = BridgeFactory(svc)
        bridges = factory.create_all()
        assert "library" in bridges
        assert "queue" in bridges
        assert "history" in bridges
        assert "playlists" in bridges
        assert "smart_tagging" in bridges
        assert "global_search" in bridges
        assert "job_bridge" in bridges
        assert "radio" in bridges
        assert "lyrics" in bridges
        assert "mix" in bridges
        assert "home" in bridges
        assert "home_audio" in bridges
        assert len(bridges) >= 30

    def test_query_service_full_roles(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService, _sort_col, _TRACK_SORT
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [5]
        db.conn.execute.return_value.fetchall.return_value = []
        qs = LibraryQueryService(db=db)
        assert qs.count_tracks() == 5
        assert qs.count_albums() == 5
        assert qs.count_artists() == 5
        assert qs.fetch_tracks() == []
        assert qs.fetch_albums() == []
        assert qs.fetch_artists() == []
        assert len(_TRACK_SORT) >= 7
        assert _sort_col("title") == "LOWER(COALESCE(title, ''))"

    def test_query_service_internal_methods(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [1, "/path/song.flac", "Title", "Artist", "Album", 180, "uid", "key"]
        db.conn.execute.return_value.fetchall.return_value = []
        qs = LibraryQueryService(db=db)
        track = qs.fetch_track_internal(1)
        assert track is not None
        assert track["filepath"] == "/path/song.flac"
        assert qs.fetch_album_tracks_internal("key") == []
        assert qs.fetch_artist_tracks_internal("Artist") == []
        assert qs.fetch_folder_tracks_internal("/path") == []

    def test_query_service_public_details(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [0]
        db.conn.execute.return_value.fetchall.return_value = [[1, "/path/s.flac", "T", "A", "Al", 180, "uid"]]
        qs = LibraryQueryService(db=db)
        detail = qs.fetch_album_detail("key")
        assert detail is not None
        assert "album_key" in detail
        assert "filepath" not in str(detail.get("tracks", [{}])[0])

    def test_query_service_filters(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [0]
        db.conn.execute.return_value.fetchall.return_value = []
        qs = LibraryQueryService(db=db)
        assert qs.count_tracks(search="test") == 0
        assert qs.count_tracks(artist="Artist") == 0
        assert qs.count_tracks(album="Album") == 0
        assert qs.count_tracks(genre="Rock") == 0
        assert qs.count_tracks(fmt="flac") == 0
        assert qs.count_tracks(missing_artist=True) == 0
        assert qs.count_tracks(missing_album=True) == 0

    def test_query_service_folder_methods(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [0]
        db.conn.execute.return_value.fetchall.return_value = []
        qs = LibraryQueryService(db=db)
        assert qs.count_folders() == 0
        assert qs.count_folders(parent_path="/music") == 0
        assert qs.fetch_folders() == []


class TestWave9PagedModels:
    def test_track_model_roles(self):
        from ui_qml.models.TrackListModel import TrackListModel
        model = TrackListModel()
        names = model.roleNames()
        assert b"trackId" in names.values()
        assert b"title" in names.values()
        assert b"artist" in names.values()
        assert b"duration" in names.values()

    def test_album_model_roles(self):
        from ui_qml.models.AlbumListModel import AlbumListModel
        model = AlbumListModel()
        names = model.roleNames()
        assert b"albumKey" in names.values()
        assert b"title" in names.values()
        assert b"artist" in names.values()
        assert b"coverKey" in names.values()

    def test_artist_model_roles(self):
        from ui_qml.models.ArtistListModel import ArtistListModel
        model = ArtistListModel()
        names = model.roleNames()
        assert b"name" in names.values()
        assert b"trackCount" in names.values()
        assert b"albumCount" in names.values()

    def test_folder_model_roles(self):
        from ui_qml.models.FolderTreeModel import FolderTreeModel
        model = FolderTreeModel()
        names = model.roleNames()
        assert b"folderPath" in names.values()
        assert b"folderName" in names.values()
        assert b"trackCount" in names.values()

    def test_queue_model_roles(self):
        from ui_qml.models.QueueListModel import QueueListModel
        model = QueueListModel()
        names = model.roleNames()
        assert b"title" in names.values()
        assert b"filepath" in names.values()
        assert b"duration" in names.values()

    def test_history_model_roles(self):
        from ui_qml.models.HistoryListModel import HistoryListModel
        model = HistoryListModel()
        names = model.roleNames()
        assert b"title" in names.values()
        assert b"playedAt" in names.values()
        assert b"filepath" in names.values()

    def test_base_model_signals(self):
        from ui_qml.models.BasePagedListModel import BasePagedListModel
        model = BasePagedListModel()
        assert hasattr(model, 'countChanged')
        assert hasattr(model, 'loadingChanged')
        assert hasattr(model, 'errorChanged')
        assert hasattr(model, 'hasMoreChanged')
        assert hasattr(model, 'loadingMoreChanged')

    def test_track_model_data_access(self):
        from ui_qml.models.TrackListModel import TrackListModel
        model = TrackListModel()
        model._items = [{"track_id": 1, "title": "Song", "artist": "A", "album_key": "k", "duration": 180}]
        idx = model.index(0)
        assert model.data(idx, model.TrackIdRole) == 1
        assert model.data(idx, model.TitleRole) == "Song"
        assert model.data(idx, model.ArtistRole) == "A"

    def test_album_model_data_access(self):
        from ui_qml.models.AlbumListModel import AlbumListModel
        model = AlbumListModel()
        model._items = [{"album_key": "k", "title": "Album", "artist": "A", "year": 2020, "track_count": 10, "duration": 3600, "cover_key": "k"}]
        idx = model.index(0)
        assert model.data(idx, model.AlbumKeyRole) == "k"
        assert model.data(idx, model.TitleRole) == "Album"


class TestWave9Bridges:
    def test_library_bridge_default_state(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        assert bridge.songCount == 0
        assert bridge.albumCount == 0
        assert bridge.artistCount == 0
        assert bridge.errorMessage == ""

    def test_library_bridge_setsort(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        result = bridge.sortBy("year")
        assert result.get("ok") is True
        assert bridge.activeSortKey == "year"

    def test_playlists_bridge_default(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        bridge = PlaylistsBridge()
        assert bridge.playlists == []

    def test_queue_bridge_default(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        bridge = QueueBridge()
        assert bridge.queueCount == 0

    def test_history_bridge_default(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        bridge = HistoryBridge()
        assert bridge.historyCount == 0

    def test_radio_bridge_default(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        bridge = RadioBridge()
        assert bridge.stations == []

    def test_lyrics_bridge_default(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        assert bridge.status == "idle"

    def test_mix_bridge_default(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        bridge = MixBridge()
        cats = bridge.categories
        assert isinstance(cats, list)
        assert len(cats) > 0
        assert bridge.currentSongs == []

    def test_smart_tagging_bridge_default(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        assert bridge.status == "idle"
        assert bridge.suggestions == []

    def test_global_search_bridge_default(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        bridge = GlobalSearchBridge()
        assert bridge.results == []
        assert bridge.isSearching is False

    def test_action_registry_default(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        registry = ActionRegistry()
        actions = registry.actions
        assert len(actions) >= 20

    def test_job_bridge_default(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge()
        assert bridge.jobs == []
        assert bridge.activeCount == 0

    def test_metadata_bridge_default(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        bridge = MetadataBridge()
        assert bridge.hasSelection is False
        assert bridge.isLoading is False

    def test_home_bridge_default(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        bridge = HomeBridge()
        assert bridge.libraryAlbums == 0
        assert bridge.libraryTracks == 0


class TestWave9MetadataAdapter:
    def test_load_tags(self):
        from ui_qml_bridge.metadata_tag_adapter import load_tags
        result = load_tags("/nonexistent/file.flac")
        assert result is None or hasattr(result, 'error')

    def test_create_backup_nonexistent(self):
        from ui_qml_bridge.metadata_tag_adapter import create_backup
        result = create_backup("/nonexistent/file.flac")
        assert result is None

    def test_backup_verify_rollback_cycle(self):
        from ui_qml_bridge.metadata_tag_adapter import create_backup, rollback
        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".flac", delete=False)  # noqa: SIM115
        tmp.write(b"test data")
        tmp.close()
        backup = create_backup(tmp.name)
        assert backup is not None
        assert os.path.exists(backup)
        with open(tmp.name, "w") as f:
            f.write("modified")
        rb = rollback(backup, tmp.name)
        assert rb.get("ok") is True
        with open(tmp.name) as f:
            assert f.read() == "test data"
        os.unlink(tmp.name)
        os.unlink(backup)

    def test_error_catalog(self):
        from ui_qml_bridge.error_catalog import safe_message
        msg = safe_message("FILE_NOT_FOUND")
        assert msg and len(msg) > 0
        fallback = safe_message("UNKNOWN_CODE")
        assert fallback == "UNKNOWN_CODE"


class TestWave9SmokeImport:
    def test_qml_main_import(self):
        import ui_qml_bridge.qml_main
        assert hasattr(ui_qml_bridge.qml_main, 'main')

    def test_runtime_smoke_import(self):
        import scripts.qml_full_runtime_smoke
        assert hasattr(scripts.qml_full_runtime_smoke, 'main')

    def test_library_refresh_coordinator(self):
        from ui_qml_bridge.library_refresh_coordinator import LibraryRefreshCoordinator
        coord = LibraryRefreshCoordinator()
        assert coord is not None
        coord.refresh_all()
        coord.refresh_after_playlist_change()
        coord.refresh_after_metadata(1)
        coord.activate_songs()
        coord.activate_albums()
        coord.activate_folders()
