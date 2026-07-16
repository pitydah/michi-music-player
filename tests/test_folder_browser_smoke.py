"""Smoke tests for FolderBrowserWidget — instantiation, signals, filters, context menu.

Uses pytest-qt when available. Falls back gracefully with skip decorator.
"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest
from pytestqt.qt_compat import qt_api

from library.folder_models import FolderHealth
from legacy_widgets.ui.folder_browser import FolderBrowserWidget


@pytest.fixture
def widget(qtbot):
    """Create a FolderBrowserWidget with qtbot."""
    w = FolderBrowserWidget()
    qtbot.addWidget(w)
    return w


class TestInstantiation:
    def test_create_without_db(self, widget):
        assert widget is not None
        assert widget._tree is not None
        assert widget._tree.columnCount() == 9

    def test_column_headers(self, widget):
        headers = [widget._tree.headerItem().text(i) for i in range(9)]
        assert "Nombre" in headers
        assert "Estado" in headers
        assert "Tipo" in headers
        assert "Indexado" in headers
        assert "Ruta" in headers

    def test_create_with_db(self, qtbot):
        db = MagicMock()
        db.conn = MagicMock()
        w = FolderBrowserWidget(db=db)
        qtbot.addWidget(w)
        assert w._db is not None

    def test_set_db(self, widget):
        db = MagicMock()
        widget.set_db(db)
        assert widget._db is not None


class TestSignals:
    def test_folder_loaded_emitted(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            with qtbot.waitSignal(widget.folder_loaded, timeout=500) as blocker:
                widget._load(tmpdir)
            assert blocker.signal_triggered
            assert blocker.args[0] == tmpdir

    def test_scan_requested_emitted(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            widget._root = tmpdir
            with qtbot.waitSignal(widget.scan_requested, timeout=500) as blocker:
                widget._scan_btn.click()
            assert blocker.signal_triggered

    def test_open_file_manager_requested(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            widget._root = tmpdir
            with qtbot.waitSignal(widget.open_file_manager_requested, timeout=500) as blocker:
                widget._btn_open_fm.click()
            assert blocker.signal_triggered

    def test_problem_report_emits_path_string(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            widget._root = tmpdir
            with qtbot.waitSignal(widget.problem_report_requested, timeout=500) as blocker:
                widget._btn_problems.click()
            assert blocker.signal_triggered
            assert isinstance(blocker.args[0], str)


class TestHealthPanel:
    def test_update_health_none(self, widget):
        widget.update_health(None)
        assert widget._health_score.text() == ""

    def test_update_health_excellent(self, widget):
        h = FolderHealth(path="/tmp", exists=True, score=100,
                         status="excellent")
        widget.update_health(h)
        assert "100" in widget._health_score.text()
        assert widget._health_status_lbl.text() != ""

    def test_update_health_with_recommendations(self, widget):
        from library.folder_models import FolderActionRecommendation
        h = FolderHealth(path="/tmp", exists=True, score=60,
                         status="attention", audio_count=5,
                         unindexed_audio_count=3,
                         recommended_actions=[
                             FolderActionRecommendation(
                                 action="scan_folder", label="Escanear",
                                 description="3 sin indexar")])
        widget.update_health(h)
        assert "Escanear" in widget._health_recs.text()

    def test_update_health_button_visibility(self, widget):
        h = FolderHealth(path="/tmp", exists=True, score=100,
                         status="excellent", is_inside_library_root=True)
        widget.update_health(h)
        assert widget._btn_add_root.isVisible() is False


class TestFilters:
    def test_set_filter_text(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            open(os.path.join(tmpdir, "other.txt"), "w").close()
            widget._load(tmpdir)
            assert widget._tree.topLevelItemCount() > 0
            widget.set_filter("song")
            # After filter, at least one item should be visible
            visible = any(not widget._tree.topLevelItem(i).isHidden()
                         for i in range(widget._tree.topLevelItemCount()))
            assert visible

    def test_view_filter_all(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            widget._load(tmpdir)
            widget._set_view_filter("all")
            assert widget._view_filter == "all"

    def test_audio_lab_button_hidden_by_default(self, widget):
        assert widget._btn_audio_lab.isVisible() is False


class TestContextMenuSmoke:
    def test_context_menu_folder(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
            widget._load(tmpdir)
            item = widget._tree.topLevelItem(0)
            if item:
                pos = widget._tree.visualItemRect(item).topLeft()
                widget._tree.customContextMenuRequested.emit(pos)
                # No crash is the test

    def test_context_menu_does_not_crash_no_item(self, widget, qtbot):
        pos = widget._tree.viewport().mapFromGlobal(qt_api.QtCore.QPoint(0, 0))
        widget._tree.customContextMenuRequested.emit(pos)
        # No crash


class TestFolderEntryDisplay:
    def test_shows_all_entry_types(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("track.flac", "unknown.ape", "cover.jpg",
                         "folder.png", "playlist.m3u", "album.cue",
                         "rip.log", "notes.txt"):
                open(os.path.join(tmpdir, name), "w").close()
            widget._load(tmpdir)
            names = set()
            for i in range(widget._tree.topLevelItemCount()):
                names.add(widget._tree.topLevelItem(i).text(0))
            assert "track.flac" in names
            assert "cover.jpg" in names
            assert "folder.png" in names
            assert "playlist.m3u" in names
            assert "album.cue" in names
            assert "rip.log" in names
            assert "notes.txt" in names

    def test_audio_types_labels(self, widget, qtbot):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "track.flac"), "w").close()
            widget._load(tmpdir)
            item = widget._tree.topLevelItem(0)
            if item:
                assert item.text(2) in ("Canci\u00f3n",)
