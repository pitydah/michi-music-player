"""QueueListModel incremental update tests — verifies targeted signals."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml.models.QueueListModel import QueueListModel

pytestmark = [pytest.mark.qml_module("queue")]


def _make_model(items=None, current_index=-1):
    items = items or []
    service = MagicMock()
    state = {"items": list(items), "current_index": current_index}
    service.get_state.return_value = state
    service.subscribe.return_value = MagicMock()
    return QueueListModel(queue_service=service), service


class TestIncrementalCurrentIndexChanged:
    """Verify targeted dataChanged instead of full reset for index changes."""

    def test_current_index_change_emits_data_changed(self):
        model, service = _make_model(
            [{"title": "A"}, {"title": "B"}, {"title": "C"}],
            current_index=0,
        )
        spy = MagicMock()
        model.dataChanged.connect(spy)
        # Simulate current index change from 0 to 1
        handler = service.subscribe.call_args[0][0]
        handler("currentIndexChanged", {
            "operation": "play_from_index",
            "items": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
            "current_index": 1,
        })
        spy.assert_called()

    def test_current_index_change_does_not_emit_refreshing(self):
        model, service = _make_model(
            [{"title": "A"}, {"title": "B"}],
            current_index=0,
        )
        spy = MagicMock()
        model.refreshingChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("currentIndexChanged", {
            "operation": "next",
            "items": [{"title": "A"}, {"title": "B"}],
            "current_index": 1,
        })
        spy.assert_not_called()

    def test_structural_change_triggers_full_refresh(self):
        model, service = _make_model(
            [{"title": "A"}],
            current_index=0,
        )
        spy = MagicMock()
        model.countChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        # queueChanged triggers refresh (structural change)
        handler("queueChanged", {
            "operation": "add",
            "items": [{"title": "A"}, {"title": "B"}],
            "current_index": 0,
        })
        # Full refresh emits countChanged
        assert spy.called

    def test_same_index_no_emission(self):
        model, service = _make_model(
            [{"title": "A"}, {"title": "B"}],
            current_index=1,
        )
        spy = MagicMock()
        model.dataChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        # Same index — no change, no emission
        handler("currentIndexChanged", {
            "operation": "backend_progress",
            "items": [{"title": "A"}, {"title": "B"}],
            "current_index": 1,
        })
        spy.assert_not_called()


class TestQueueListModelRoles:
    """Verify role names and data access."""

    def test_role_names_match_contract(self):
        model, _ = _make_model()
        roles = model.roleNames()
        expected_roles = [
            b"trackId", b"trackUid", b"title", b"artist", b"album",
            b"albumKey", b"duration", b"current", b"position",
            b"coverKey", b"sourceType",
        ]
        for role in expected_roles:
            assert role in roles.values(), f"Missing role: {role}"

    def test_data_returns_correct_values(self):
        items = [{"title": "Test", "artist": "Artist", "duration": 180}]
        model, _ = _make_model(items, current_index=0)
        from PySide6.QtCore import Qt
        index = model.index(0, 0)
        assert model.data(index, Qt.DisplayRole) == "Test"

    def test_data_returns_none_for_invalid_index(self):
        model, _ = _make_model()
        from PySide6.QtCore import Qt
        index = model.index(0, 0)
        assert model.data(index, Qt.DisplayRole) is None

    def test_count_matches_items(self):
        items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        model, _ = _make_model(items)
        assert model.count == 3

    def test_empty_model_has_zero_count(self):
        model, _ = _make_model([])
        assert model.count == 0


class TestQueueListModelRefresh:
    """Verify refresh behavior."""

    def test_shutdown_unsubscribes(self):
        model, service = _make_model()
        unsub = service.subscribe.return_value
        model.shutdown()
        unsub.assert_called_once()

    def test_double_shutdown_is_safe(self):
        model, service = _make_model()
        unsub = service.subscribe.return_value
        model.shutdown()
        model.shutdown()  # Should not raise
        unsub.assert_called_once()

    def test_operation_failed_does_not_update(self):
        model, service = _make_model([{"title": "A"}], current_index=0)
        handler = service.subscribe.call_args[0][0]
        original_state = dict(model._queue_state)
        handler("operationFailed", {"error": "test"})
        # State should not change
        assert model._queue_state.get("items") == original_state.get("items")
