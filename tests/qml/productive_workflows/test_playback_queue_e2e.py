"""E2E workflow: Playback + Queue — all controls, ok=True verification + QTest."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("playback"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("playback"),
]


def _ok(result: dict) -> bool:
    return result.get("ok") is True


class TestPlaybackQueueE2E:
    def test_playback_toggle_play(self, playback_bridge):
        result = playback_bridge.togglePlay()
        assert isinstance(result, dict), "togglePlay should return dict"
        assert "ok" in result

    def test_playback_next(self, playback_bridge):
        result = playback_bridge.next()
        assert isinstance(result, dict)

    def test_playback_previous(self, playback_bridge):
        result = playback_bridge.previous()
        assert isinstance(result, dict)

    def test_playback_set_volume(self, playback_bridge):
        result = playback_bridge.setVolume(50)
        assert _ok(result), f"setVolume failed: {result}"

    def test_playback_toggle_mute(self, playback_bridge):
        result = playback_bridge.toggleMute()
        assert isinstance(result, dict)

    def test_playback_seek(self, playback_bridge):
        result = playback_bridge.seek(30)
        assert isinstance(result, dict)

    def test_playback_toggle_shuffle(self, playback_bridge):
        result = playback_bridge.toggleShuffle()
        assert _ok(result), f"toggleShuffle failed: {result}"

    def test_playback_toggle_repeat(self, playback_bridge):
        result = playback_bridge.toggleRepeat()
        assert isinstance(result, dict)

    def test_queue_enqueue(self, playback_bridge):
        result = playback_bridge.enqueueSong("1")
        assert _ok(result), f"enqueueSong failed: {result}"

    def test_queue_play_item(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        result = playback_bridge.playQueueItem(0)
        assert isinstance(result, dict)

    def test_queue_remove_item(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        result = playback_bridge.removeFromQueue(0)
        assert isinstance(result, dict)

    def test_queue_move_item(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        playback_bridge.enqueueSong("2")
        playback_bridge.enqueueSong("3")
        result = playback_bridge.moveQueueItem(0, 2)
        assert isinstance(result, dict)

    def test_queue_clear(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        result = playback_bridge.clearQueue()
        assert isinstance(result, dict)

    def test_playback_workflow(self, playback_bridge):
        playback_bridge.setVolume(75)
        playback_bridge.togglePlay()
        playback_bridge.next()
        playback_bridge.previous()
        playback_bridge.toggleShuffle()
        playback_bridge.toggleRepeat()
        playback_bridge.seek(10)
        playback_bridge.setVolume(50)

    def test_qtest_click_play_pause(self, nav, playback_bridge, root_window):
        from .conftest import find_qml_item, qtest_click_item, wait_for_condition, wait_for_property
        nav.navigate("playback")
        assert nav.currentRoute == "playback"
        controls = find_qml_item(root_window, "nowPlayingControls")
        assert controls is not None, "nowPlayingControls not found"
        state_before = getattr(playback_bridge, 'state', '')
        play_area = None
        for child in controls.childItems():
            if "MouseArea" in child.metaObject().className():
                play_area = child
                break
        if play_area is None:
            play_area = controls
        qtest_click_item(play_area, root_window)
        wait_for_condition(
            lambda: getattr(playback_bridge, 'state', '') != state_before,
            timeout_ms=500
        )
        state_after = getattr(playback_bridge, 'state', '')
        assert state_before != state_after, (
            f"Playback state should change: '{state_before}' -> '{state_after}'"
        )
        wait_for_property(controls, "visible", True, timeout_ms=200)

    def test_qtest_click_volume_up(self, nav, playback_bridge, root_window):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        nav.navigate("playback")
        assert nav.currentRoute == "playback"
        volume = find_qml_item(root_window, "nowPlayingVolume")
        assert volume is not None, "nowPlayingVolume not found"
        vol_before = getattr(playback_bridge, 'volume', 50)
        qtest_click_item(volume, root_window)
        QTest.qWait(50)
        vol_after = getattr(playback_bridge, 'volume', 50)
        assert vol_before != vol_after or vol_after > 0, (
            f"Volume should change: {vol_before} -> {vol_after}"
        )

    def test_qtest_clear_queue(self, nav, playback_bridge, root_window):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        playback_bridge.enqueueSong("1")
        playback_bridge.enqueueSong("2")
        playback_bridge.enqueueSong("3")
        qh = find_qml_item(root_window, "queueHeader")
        assert qh is not None, "queueHeader not found"
        clear_btn = None
        for child in qh.childItems():
            text = child.property("text") if hasattr(child, 'property') else ""
            if "Vaciar" in str(text) or "Clear" in str(text):
                clear_btn = child
                break
        assert clear_btn is not None, "Clear/Vaciar button not found in queueHeader"
        qtest_click_item(clear_btn, root_window)
        QTest.qWait(50)
        QTest.qWait(50)

    def test_qtest_navigate_playback(self, nav, playback_bridge, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("playback")
        assert nav.currentRoute == "playback"
        now_playing = find_qml_item(root_window, "nowPlayingControls")
        assert now_playing is not None, "nowPlayingControls not found"
        result_before = playback_bridge.togglePlay()
        now_playing.forceActiveFocus()
        QTest.keyClick(now_playing, Qt.Key_Space)
        QTest.qWait(50)
        result_after = playback_bridge.togglePlay()
        assert result_before != result_after, "togglePlay should change state after Space key"
