"""Tests for LibraryWatcherController."""
from __future__ import annotations


class FakeDB:
    def __init__(self):
        self.deleted = None

    def mark_files_deleted(self, paths, deleted_at=None):
        self.deleted = paths


class FakeFileActions:
    def __init__(self):
        self.added = None

    def add_file_list(self, paths):
        self.added = paths


class FakeLibraryController:
    def __init__(self):
        self.reasons = []

    def reload_after_change(self, reason):
        self.reasons.append(reason)


class FakeToast:
    def __init__(self):
        self.messages = []

    def show(self, text, level):
        self.messages.append((text, level))


def test_on_files_added():
    from legacy_widgets.ui.controllers.legacy_controllers.library_watcher_controller import LibraryWatcherController
    db = FakeDB()
    fa = FakeFileActions()
    lc = FakeLibraryController()
    toast = FakeToast()
    ctrl = LibraryWatcherController(db, fa, lc, toast_service=toast)

    ctrl.on_files_added(["/path/a.flac", "/path/b.mp3"])

    assert fa.added == ["/path/a.flac", "/path/b.mp3"]
    assert lc.reasons == ["watcher_added"]
    assert toast.messages == [("2 archivos nuevos detectados", "info")]


def test_on_files_added_empty():
    from legacy_widgets.ui.controllers.legacy_controllers.library_watcher_controller import LibraryWatcherController
    db = FakeDB()
    fa = FakeFileActions()
    lc = FakeLibraryController()
    ctrl = LibraryWatcherController(db, fa, lc)

    ctrl.on_files_added([])

    assert fa.added is None
    assert lc.reasons == []


def test_on_files_removed():
    from legacy_widgets.ui.controllers.legacy_controllers.library_watcher_controller import LibraryWatcherController
    db = FakeDB()
    fa = FakeFileActions()
    lc = FakeLibraryController()
    ctrl = LibraryWatcherController(db, fa, lc)

    ctrl.on_files_removed(["/path/gone.flac"])

    assert db.deleted == ["/path/gone.flac"]
    assert lc.reasons == ["watcher_removed"]


def test_on_files_removed_empty():
    from legacy_widgets.ui.controllers.legacy_controllers.library_watcher_controller import LibraryWatcherController
    db = FakeDB()
    fa = FakeFileActions()
    lc = FakeLibraryController()
    ctrl = LibraryWatcherController(db, fa, lc)

    ctrl.on_files_removed([])

    assert db.deleted is None
    assert lc.reasons == []


def test_on_files_modified():
    from legacy_widgets.ui.controllers.legacy_controllers.library_watcher_controller import LibraryWatcherController
    db = FakeDB()
    fa = FakeFileActions()
    lc = FakeLibraryController()
    ctrl = LibraryWatcherController(db, fa, lc)

    ctrl.on_files_modified(["/path/changed.flac"])

    assert fa.added == ["/path/changed.flac"]
    assert lc.reasons == ["watcher_modified"]


def test_on_files_modified_empty():
    from legacy_widgets.ui.controllers.legacy_controllers.library_watcher_controller import LibraryWatcherController
    db = FakeDB()
    fa = FakeFileActions()
    lc = FakeLibraryController()
    ctrl = LibraryWatcherController(db, fa, lc)

    ctrl.on_files_modified([])

    assert fa.added is None
    assert lc.reasons == []
