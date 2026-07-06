"""E2E: verify all Wave IX bridges, models, and services import and respond correctly."""
from __future__ import annotations

import pytest
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
        assert b"duration" in names.values()
        assert b"filepath" not in names.values()

    def test_history_model_roles(self):
        from ui_qml.models.HistoryListModel import HistoryListModel
        model = HistoryListModel()
        names = model.roleNames()
        assert b"title" in names.values()
        assert b"playedAt" in names.values()
        assert b"filepath" not in names.values()

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


class TestWave10RealVerticalFlow:
    """Real E2E with SQLite temp DB, WorkerManager, QueryExecutor, models."""

    @pytest.fixture
    def library_db(self, tmp_path):
        import sqlite3
        db_path = tmp_path / "test_music.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=OFF")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                directory TEXT NOT NULL DEFAULT '',
                ext TEXT NOT NULL DEFAULT '',
                kind TEXT NOT NULL DEFAULT 'audio',
                size INTEGER DEFAULT 0,
                mtime REAL DEFAULT 0,
                duration REAL DEFAULT 0,
                channels INTEGER DEFAULT 2,
                sample_rate INTEGER DEFAULT 44100,
                bitrate INTEGER DEFAULT 320,
                title TEXT DEFAULT '',
                artist TEXT DEFAULT '',
                album TEXT DEFAULT '',
                albumartist TEXT DEFAULT '',
                album_key TEXT DEFAULT '',
                year INTEGER DEFAULT 0,
                genre TEXT DEFAULT '',
                track_number INTEGER DEFAULT 0,
                track_total INTEGER DEFAULT 0,
                disc_number INTEGER DEFAULT 0,
                disc_total INTEGER DEFAULT 0,
                bit_depth INTEGER DEFAULT 16,
                play_count INTEGER DEFAULT 0,
                last_played REAL DEFAULT 0,
                track_uid TEXT DEFAULT '',
                created_at REAL DEFAULT (strftime('%%s','now')),
                deleted_at REAL
            );
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cover_path TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at REAL DEFAULT (strftime('%%s','now'))
            );
            CREATE TABLE IF NOT EXISTS playlist_items (
                playlist_id INTEGER NOT NULL REFERENCES playlists(id),
                filepath TEXT NOT NULL,
                track_id INTEGER REFERENCES media_items(id),
                position INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS play_history (
                track_id TEXT NOT NULL,
                device TEXT DEFAULT 'desktop',
                played_at REAL DEFAULT (strftime('%%s','now'))
            );
            CREATE TABLE IF NOT EXISTS queue_state (
                id INTEGER PRIMARY KEY,
                filepath TEXT NOT NULL
            );
        """)
        yield conn
        conn.close()

    def _populate(self, conn, artists=20, albums_per_artist=2, tracks_per_album=25):
        import random
        random.seed(42)
        formats = ["flac", "mp3", "wav", "aac"]
        genres = ["Rock", "Pop", "Jazz", "Classical", "Electronic", "Hip Hop", "Blues", "Reggae", "Folk", "Metal", "R&B"]
        folders = ["/music", "/music/Rock", "/music/Jazz", "/music/Electronic", "/music/Pop"]
        conn.execute("DELETE FROM media_items")
        total = 0
        for a in range(artists):
            artist_name = f"Artist_{a}"
            for ab in range(albums_per_artist):
                album_name = f"Album_{a}_{ab}"
                album_key = f"key_{a}_{ab}"
                folder = folders[a % len(folders)]
                for t in range(tracks_per_album):
                    total += 1
                    ext = random.choice(formats)
                    fp = f"{folder}/track_{total}.{ext}"
                    title = f"Track_{total}"
                    genre = random.choice(genres)
                    year = 1990 + a
                    conn.execute(
                        """INSERT INTO media_items
                        (filepath, filename, directory, ext, title, artist, album,
                         albumartist, album_key, year, genre, track_number, track_uid, duration)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (fp, f"track_{total}.{ext}", folder, f".{ext}",
                         title, artist_name, album_name, artist_name,
                         album_key, year, genre, t + 1, f"uid_{total}", random.uniform(120, 600))
                    )
        conn.commit()
        return total

    def _make_db_mock(self, conn, db_path):
        class FakeDB:
            def __init__(s):
                s.conn = conn
                s.db_path = str(db_path)
            def get_playlists(s):
                return [{"id": r[0], "name": r[1]} for r in
                        s.conn.execute("SELECT id, name FROM playlists").fetchall()]
            def create_playlist(s, name):
                cur = s.conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
                s.conn.commit()
                return cur.lastrowid
            def add_track_to_playlist(s, pid, filepath="", track_id=None):
                if track_id:
                    s.conn.execute("INSERT INTO playlist_items (playlist_id, track_id, filepath, position) VALUES (?,?,?,?)",
                                   (pid, track_id, filepath or "", 0))
                elif filepath:
                    s.conn.execute("INSERT INTO playlist_items (playlist_id, filepath, position) VALUES (?,?,?)",
                                   (pid, filepath, 0))
                s.conn.commit()
            def delete_playlist(s, pid):
                s.conn.execute("DELETE FROM playlist_items WHERE playlist_id=?", (pid,))
                s.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
                s.conn.commit()
            def get_playlist_items(s, pid):
                rows = s.conn.execute(
                    "SELECT pi.filepath, pi.track_id, pi.position, m.id, m.title, m.artist, m.album, m.duration, m.track_uid "
                    "FROM playlist_items pi LEFT JOIN media_items m ON pi.track_id = m.id OR pi.filepath = m.filepath "
                    "WHERE pi.playlist_id=? ORDER BY pi.position", (pid,)
                ).fetchall()
                return [{"filepath": r[0], "id": r[3], "title": r[4], "artist": r[5],
                         "album": r[6], "duration": r[7], "track_uid": r[8]} for r in rows]
            def get_play_history(s, device="desktop"):
                rows = s.conn.execute(
                    "SELECT track_id, played_at FROM play_history ORDER BY played_at DESC LIMIT 100"
                ).fetchall()
                return [{"track_id": r[0], "played_at": r[1]} for r in rows]
        return FakeDB()

    def test_real_flow_track_refresh(self, library_db, tmp_path):
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.instance() or QCoreApplication()
        total = self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.TrackListModel import TrackListModel
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = TrackListModel(query_service=qs, query_executor=qe)
        assert model.count == 0
        assert model.loading is False
        model.refresh()
        assert model.loading is False  # sync fallback
        assert model.totalCount == total
        assert model.count == model._page_size
        assert model.hasMore is True
        assert model.errorCode == ""

    def test_real_flow_fetch_more(self, library_db, tmp_path):
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.instance() or QCoreApplication()
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.TrackListModel import TrackListModel
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh()
        assert model.loading is False
        assert model.count == model._page_size
        old_count = model.count
        model.fetchMore()
        assert model.loadingMore is False  # sync fallback
        assert model.count > old_count
        assert model.hasMore is True

    def test_real_flow_search(self, library_db, tmp_path):
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.TrackListModel import TrackListModel
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = TrackListModel(query_service=qs, query_executor=qe)
        search_term = "Track_5"
        model.refresh(search=search_term)
        assert model.loading is False
        assert model.totalCount > 0
        for i in range(model.count):
            idx = model.index(i)
            title = model.data(idx, model.TitleRole) or ""
            assert search_term.lower() in title.lower()

    def test_real_flow_sort_desc(self, library_db, tmp_path):
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.TrackListModel import TrackListModel
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh(sort="year", asc=False)
        assert model.loading is False
        assert model.count > 1
        first = model.data(model.index(0), model.YearRole) or 0
        last = model.data(model.index(model.count - 1), model.YearRole) or 0
        assert first >= last

    def test_real_flow_artist_filter(self, library_db, tmp_path):
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.TrackListModel import TrackListModel
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh(artist="Artist_0")
        assert model.loading is False
        assert model.totalCount == 50
        for i in range(model.count):
            artist = model.data(model.index(i), model.ArtistRole)
            assert artist == "Artist_0"

    def test_real_flow_album_filter(self, library_db, tmp_path):
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.TrackListModel import TrackListModel
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh(album="Album_0_0")
        assert model.loading is False
        assert model.totalCount == 25

    def test_real_flow_format_filter(self, library_db, tmp_path):
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.TrackListModel import TrackListModel
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh(fmt="flac")
        assert model.loading is False
        assert model.totalCount > 0
        for i in range(min(model.count, 20)):
            fmt = model.data(model.index(i), model.FormatRole) or ""
            assert fmt == "FLAC"

    def test_real_flow_album_model(self, library_db, tmp_path):
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.AlbumListModel import AlbumListModel
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = AlbumListModel(query_service=qs, query_executor=qe)
        model.refresh()
        assert model.loading is False
        assert model.totalCount == 40
        assert model.count > 0

    def test_real_flow_artist_model(self, library_db, tmp_path):
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml.models.ArtistListModel import ArtistListModel
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qe = QueryExecutor()
        qs = LibraryQueryService(db, db_path=str(db_path))
        model = ArtistListModel(query_service=qs, query_executor=qe)
        model.refresh()
        assert model.loading is False
        assert model.totalCount == 20
        assert model.count > 0

    def test_real_flow_album_detail(self, library_db, tmp_path):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        qs = LibraryQueryService(db, db_path=str(db_path))
        detail = qs.fetch_album_detail("key_0_0")
        assert detail is not None
        assert detail["album_key"] == "key_0_0"
        assert detail["track_count"] == 25
        for t in detail["tracks"]:
            assert "filepath" not in t

    def test_real_flow_album_play(self, library_db, tmp_path):
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.instance() or QCoreApplication()
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        from core.worker_manager import WorkerManager
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.library_bridge import LibraryBridge
        wm = WorkerManager()
        qe = QueryExecutor(worker_manager=wm)
        qs = LibraryQueryService(db, db_path=str(db_path))

        class FakePlayer:
            def __init__(s):
                s.enqueued = []
            def enqueue(s, paths, play_now=False):
                s.enqueued = list(paths)

        player = FakePlayer()
        bridge = LibraryBridge(db=db, playback_ctrl=player,
                               query_service=qs, query_executor=qe)
        result = bridge.playAlbum("key_0_0")
        assert result.get("ok") is True
        assert result.get("count") == 25
        assert len(player.enqueued) == 25
        for fp in player.enqueued:
            assert "/music/" in fp

    @pytest.mark.xfail(reason="Wave IX: playPlaylist usa formato público sin filepath (Fase 7)")
    def test_real_flow_playlist_create_play(self, library_db, tmp_path):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)

        class FakePlayer:
            def __init__(s):
                s.enqueued = []
            def enqueue(s, paths, play_now=False):
                s.enqueued = list(paths)

        player = FakePlayer()
        bridge = PlaylistsBridge(db=db, player_service=player)
        bridge.refresh()
        result = bridge.createPlaylist("Test Playlist")
        assert result.get("ok") is True
        pid = result["id"]
        rows = db.conn.execute("SELECT id, filepath FROM media_items LIMIT 5").fetchall()
        for row in rows:
            bridge.addTrackToPlaylist(pid, filepath=row[1])
        play_result = bridge.playPlaylist(pid)
        assert play_result.get("ok") is True
        assert len(player.enqueued) == 5

    def test_real_flow_queue_history(self, library_db, tmp_path):
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.instance() or QCoreApplication()
        self._populate(library_db)
        db_path = tmp_path / "test_music.db"
        db = self._make_db_mock(library_db, db_path)
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.history_bridge import HistoryBridge

        class FakePlayer:
            def get_queue(s):
                return [{"track_id": i, "title": f"Track_{i}", "artist": "Artist_0",
                         "album": "Album_0", "duration": 200}
                        for i in range(50)]

        player = FakePlayer()
        qbridge = QueueBridge(player_service=player)
        qbridge.refresh()
        assert qbridge.queueCount == 50

        hbridge = HistoryBridge(db=db)
        library_db.execute(
            "INSERT INTO play_history (track_id) VALUES (?)", ("/music/track_1.flac",))
        hbridge.refresh()
        assert hbridge.historyCount == 1
