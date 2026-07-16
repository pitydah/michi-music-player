"""Verify newly connected services work through bridges."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestLibraryServiceBridge:
    def test_library_bridge_has_library_service(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert lb is not None
        svc = getattr(lb, '_library_svc', None)
        assert svc is not None, "LibraryService should be connected to LibraryBridge"
        assert hasattr(svc, 'load')

    def test_library_bridge_loadLibrary_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'loadLibrary')

    def test_library_bridge_refreshTab_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'refreshTab')


class TestSongsServiceBridge:
    def test_library_bridge_has_songs_service(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        svc = getattr(lb, '_songs_svc', None)
        assert svc is not None, "SongsService should be connected to LibraryBridge"
        assert hasattr(svc, 'load')

    def test_library_bridge_loadSongs_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'loadSongs')

    def test_library_bridge_toggleFavorite_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'toggleFavorite')


class TestTrackServiceBridge:
    def test_library_bridge_has_track_service(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        svc = getattr(lb, '_track_svc', None)
        assert svc is not None, "TrackService should be connected to LibraryBridge"
        assert hasattr(svc, 'locate_file')

    def test_library_bridge_editTrackMetadata_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'editTrackMetadata')

    def test_library_bridge_locateTrackFile_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'locateTrackFile')


class TestGenresServiceBridge:
    def test_library_bridge_has_genres_service(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        svc = getattr(lb, '_genres_svc', None)
        assert svc is not None, "GenresService should be connected to LibraryBridge"
        assert hasattr(svc, 'list_genres')

    def test_library_bridge_listGenres_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'listGenres')

    def test_library_bridge_playGenre_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'playGenre')

    def test_library_bridge_normalizeGenre_slot(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert hasattr(lb, 'normalizeGenre')


class TestFolderServiceBridge:
    def test_sources_bridge_has_folder_service(self, bootstrap):
        lsb = bootstrap._bridges.get("library_sources")
        assert lsb is not None
        svc = getattr(lsb, '_folder_svc', None)
        assert svc is not None, "FolderService should be connected to LibrarySourcesBridge"
        assert hasattr(svc, 'scan')

    def test_sources_bridge_scanFolder_slot(self, bootstrap):
        lsb = bootstrap._bridges.get("library_sources")
        assert hasattr(lsb, 'scanFolder')

    def test_sources_bridge_checkIntegrity_slot(self, bootstrap):
        lsb = bootstrap._bridges.get("library_sources")
        assert hasattr(lsb, 'checkIntegrity')
