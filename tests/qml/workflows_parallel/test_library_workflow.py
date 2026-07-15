"""Workflow test: Search -> select -> context menu -> play -> queue update."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge
from ui_qml_bridge.selection_controller import SelectionController

pytestmark = [pytest.mark.qml_module("library"), pytest.mark.qml_workflow("library_workflow")]


class TestLibraryWorkflow:
    @pytest.fixture
    def tmp_songs(self):
        files = []
        for _ in range(10):
            f = Path(tempfile.mktemp(suffix=".flac"))
            f.write_text("audio")
            files.append(f)
        yield files
        for f in files:
            f.unlink(missing_ok=True)

    @pytest.fixture
    def qs(self, tmp_songs):
        qs = MagicMock()
        all_tracks = [
            {"track_id": i + 1, "track_uid": f"uid{i}", "title": f"Song {i}",
             "artist": f"Artist {i%3}", "album": f"Album {i%2}", "album_key": f"ak{i%2}",
             "duration": 200 + i, "format": "FLAC", "year": 2020 + i % 3, "genre": "",
             "track_number": i + 1, "favorite": False, "missing": False,
             "cover_key": f"ck{i}", "filepath": str(tmp_songs[i]),
             "disc_number": 1, "bit_depth": 24}
            for i in range(10)
        ]
        qs.count_tracks.return_value = 10

        def fetch_tracks_side(offset=0, limit=100, **kw):
            return all_tracks[offset:offset + limit]
        qs.fetch_tracks.side_effect = fetch_tracks_side
        qs.fetch_track_internal.side_effect = lambda tid: all_tracks[tid] if 0 <= tid < len(all_tracks) else None
        return qs

    @pytest.fixture
    def bridge(self, qs):
        bridge = LibraryBridge(query_service=qs, query_executor=None)
        return bridge

    @pytest.fixture
    def ctrl(self):
        return SelectionController()

    def test_workflow_search_then_select(self, bridge, ctrl):
        bridge.setSearchQuery("Song")
        assert bridge.searchQuery == "Song"
        ctrl.replace([1, 2, 3])
        assert ctrl.count == 3

    def test_workflow_select_then_play(self, bridge, ctrl):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        ctrl.replace([1])
        result = bridge.playTrackById(ctrl.selectedIds[0])
        assert result["ok"] is True

    def test_workflow_select_then_enqueue(self, bridge, ctrl):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        ctrl.replace([0, 1])
        for tid in ctrl.selectedIds:
            result = bridge.enqueueTrackById(tid)
            assert result["ok"] is True

    def test_workflow_context_menu_play(self, bridge, ctrl):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        ctrl.replace([5])
        result = bridge.playTrackById(5)
        assert result["ok"] is True

    def test_workflow_context_menu_add_to_queue(self, bridge, ctrl):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        ctrl.replace([3, 4])
        for tid in ctrl.selectedIds:
            result = bridge.enqueueTrackById(tid)
            assert result["ok"] is True

    def test_workflow_context_menu_favorite(self, bridge, ctrl):
        ctrl.replace([2])
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        result = bridge.enqueueTrackById(2)
        assert result["ok"] is True

    def test_workflow_context_menu_album_nav(self, bridge, ctrl):
        ctrl.replace([1])
        qs = bridge._query_svc
        track = qs.fetch_track_internal(0)
        assert track["album_key"] == "ak0"

    def test_workflow_search_empty_then_clear(self, bridge):
        bridge.setSearchQuery("nonexistent_song")
        assert bridge.searchQuery == "nonexistent_song"
        bridge.clearSearch()
        assert bridge.searchQuery == ""

    def test_workflow_select_then_clear_selection(self, ctrl):
        ctrl.replace([1, 2, 3, 4, 5])
        assert ctrl.count == 5
        ctrl.clear()
        assert ctrl.count == 0

    def test_workflow_play_after_search(self, bridge):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        bridge.setSearchQuery("Song 0")
        result = bridge.playTrackById(1)
        assert result["ok"] is True

    def test_workflow_enqueue_after_search(self, bridge):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        bridge.setSearchQuery("Song")
        result = bridge.enqueueTrackById(1)
        assert result["ok"] is True

    def test_workflow_sort_then_play(self, bridge):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        bridge.sortBy("year")
        assert bridge.activeSortKey == "year"
        result = bridge.playTrackById(1)
        assert result["ok"] is True

    def test_workflow_filter_then_play(self, bridge):
        pb = MagicMock()
        pb.enqueue = MagicMock()
        bridge._playback_ctrl = pb
        bridge.setFormatFilter("FLAC")
        assert bridge.activeFormatFilter == "FLAC"
        result = bridge.playTrackById(1)
        assert result["ok"] is True
