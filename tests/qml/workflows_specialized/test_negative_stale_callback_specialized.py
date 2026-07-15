from __future__ import annotations
"""MX: Negative — stale callback / stale generation guard tests."""

from unittest.mock import MagicMock


def test_stale_generation_guard():
    from ui_qml_bridge.mix_bridge import MixBridge
    bridge = MixBridge()
    old_gen = bridge._generation
    bridge.cancelGeneration()
    assert bridge._generation > old_gen


def test_stale_search_request_guard():
    from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
    bridge = GlobalSearchBridge()
    old_gen = bridge._search_gen
    bridge.cancel()
    assert bridge._search_gen > old_gen


def test_stale_callback_ignored():
    bridge = MagicMock()
    bridge._request_gen = 0
    bridge.search = MagicMock(return_value={"ok": True})
    gen_before = bridge._request_gen
    bridge._request_gen = 999
    assert bridge._request_gen != gen_before


def test_stale_mix_callback():
    bridge = MagicMock()
    bridge._generation_counter = 0
    bridge.cancelGeneration()
    bridge.cancelGeneration()
    assert bridge.cancelGeneration.call_count == 2
