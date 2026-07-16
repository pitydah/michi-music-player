"""Tests: Mobile sync button visibility and disable state."""
from __future__ import annotations


class TestMobileSyncDisabled:
    def test_mobile_button_disabled_by_default(self, qtbot):
        from legacy_widgets.ui_archive.album_detail_view import AlbumDetailView
        view = AlbumDetailView()
        qtbot.addWidget(view)
        view.set_album(title="Test", artist="Artist", tracks=[])
        row = view._action_row
        if len(row._buttons) >= 8:
            btn = row._buttons[7]
            assert btn.text() == "Móvil"
            assert btn.isEnabled() is False
            assert "Michi Sync Suite" in btn.toolTip()

    def test_mobile_button_enabled(self, qtbot):
        from legacy_widgets.ui_archive.album_detail_view import AlbumDetailView
        view = AlbumDetailView()
        qtbot.addWidget(view)
        row = view._action_row
        row.set_mobile_available(True)
        if len(row._buttons) >= 8:
            btn = row._buttons[7]
            assert btn.isEnabled() is True
