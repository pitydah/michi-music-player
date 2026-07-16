"""Tests: AliasResolutionDialog — Qt dialog instantiation and interaction.

Requires pytest-qt.
"""
from PySide6.QtWidgets import QDialog

from library.artist_grouping import ArtistGroup


def _make_group(key, display_name):
    return ArtistGroup(
        key=key, display_name=display_name,
        sort_name=display_name.lower(),
        albums=[], loose_tracks=[], all_tracks=[],
        genres=[], years=[], cover_paths=[],
        total_duration=0.0, track_count=0, album_count=0,
    )


group_lookup = {
    "beatles": _make_group("beatles", "Beatles"),
    "the_beatles": _make_group("the_beatles", "The Beatles"),
}


def lookup(key):
    return group_lookup.get(key)


class TestAliasResolutionDialogQt:

    def test_instantiation(self, qtbot):
        from legacy_widgets.ui.dialogs.alias_resolution_dialog import AliasResolutionDialog
        candidates = [("the_beatles", "beatles", 1.0)]
        dialog = AliasResolutionDialog("The Beatles", candidates, lookup, None)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Resolver alias: The Beatles"

    def test_no_candidates_shows_message(self, qtbot):
        from legacy_widgets.ui.dialogs.alias_resolution_dialog import AliasResolutionDialog
        dialog = AliasResolutionDialog("Unknown", [], lookup, None)
        qtbot.addWidget(dialog)
        assert dialog.selected_key() is None

    def test_skip_returns_none(self, qtbot):
        from legacy_widgets.ui.dialogs.alias_resolution_dialog import AliasResolutionDialog
        candidates = [("the_beatles", "beatles", 1.0)]
        dialog = AliasResolutionDialog("The Beatles", candidates, lookup, None)
        qtbot.addWidget(dialog)
        dialog._on_skip()
        assert dialog.selected_key() is None
        assert dialog.result() == QDialog.Rejected

    def test_accept_returns_selected_key(self, qtbot):
        from legacy_widgets.ui.dialogs.alias_resolution_dialog import AliasResolutionDialog
        candidates = [("the_beatles", "beatles", 1.0)]
        dialog = AliasResolutionDialog("The Beatles", candidates, lookup, None)
        qtbot.addWidget(dialog)
        dialog._on_choose("beatles")
        assert dialog.selected_key() == "beatles"
        assert dialog.result() == QDialog.Accepted
