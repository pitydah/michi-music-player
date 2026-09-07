"""R6 — Queue authority cleanup seals (V4 §8-9, §72).

The Queue panel is a TEMPORARY STACK surface only:
- no navigation residue (hasPrev/hasNext/repeat/shuffle properties or
  signals — those live in the Session, driven by the transport);
- empty-state copy never implies Library playback feeds the Queue;
- the row menu is the minimal stack menu: Play queued item / Move Up /
  Move Down / Remove from Queue — no collection/entity authority;
- the superseded QueueTrackContextMenu orphan is gone.
"""

from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


def _qml(rel):
    return (QML / rel).read_text(encoding="utf-8", errors="ignore")


class TestQueuePanelMinimal:
    def test_no_navigation_residue_in_panel_or_view(self):
        panel = _qml("components/QueuePanel.qml")
        view = _qml("views/QueueView.qml")
        for token in (
            "hasPrev",
            "hasNext",
            "repeatMode",
            "shuffleEnabled",
            "previousRequested",
            "nextRequested",
            "repeatModeRequested",
            "shuffleRequested",
        ):
            assert token not in panel, f"residuo {token} en QueuePanel"
            assert token not in view, f"residuo {token} en QueueView"

    def test_session_navigation_still_owned_by_session(self):
        """El transporte (next/prev/repeat/shuffle) sigue vivo en el
        Session — lo que se removió es el residuo del PANEL."""
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )

        assert hasattr(PlaybackSessionService, "previous")
        assert hasattr(PlaybackSessionService, "next")
        assert hasattr(PlaybackSessionService, "set_repeat_mode")
        assert hasattr(PlaybackSessionService, "set_shuffle_enabled")

    def test_empty_state_copy_explains_explicit_stack(self):
        panel = _qml("components/QueuePanel.qml")
        assert "Play a track from the library" not in panel, (
            "el copy no puede sugerir que Library alimenta la cola"
        )
        assert "temporary stack" in panel
        assert "direct playback never fills it" in panel

    def test_row_menu_is_minimal_stack_menu(self):
        panel = _qml("components/QueuePanel.qml")
        # Move por índice en el menú del row + etiqueta de cola.
        assert "canMoveUp: index > 0" in panel
        assert "canMoveDown: index + 1 < root.count" in panel
        assert 'removeText: qsTr("Remove from Queue")' in panel
        assert "onMoveUpRequested: root.moveRequested(index, index - 1)" in panel
        assert "onMoveDownRequested: root.moveRequested(index, index + 1)" in panel
        # Sin capacidades de colección en el panel.
        assert "canAddToPlaylist: true" not in panel
        assert "canFavorite: true" not in panel

    def test_superseded_orphan_menu_removed(self):
        assert not (QML / "media" / "QueueTrackContextMenu.qml").exists(), (
            "el menú huérfano superseded debe haber sido removido"
        )
        for rel in ("views/QueueView.qml", "components/QueuePanel.qml"):
            assert "QueueTrackContextMenu" not in _qml(rel), rel

    def test_track_row_exposes_remove_text(self):
        row = _qml("media/TrackRow.qml")
        assert 'property string removeText: qsTr("Remove")' in row
        assert "removeText: root.removeText" in row
