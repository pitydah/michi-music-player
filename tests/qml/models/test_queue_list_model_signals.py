"""QueueListModel signal emission and preservation tests."""

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


class TestSignalEmission:
    """Verify correct signals are emitted for each event type."""

    def test_current_index_change_emits_count_changed(self):
        model, service = _make_model(
            [{"title": "A"}, {"title": "B"}], current_index=0,
        )
        spy = MagicMock()
        model.countChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("currentIndexChanged", {
            "operation": "next",
            "items": [{"title": "A"}, {"title": "B"}],
            "current_index": 1,
        })
        spy.assert_called()

    def test_structural_change_emits_count_changed(self):
        model, service = _make_model(
            [{"title": "A"}], current_index=0,
        )
        spy = MagicMock()
        model.countChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("queueChanged", {
            "operation": "add",
            "items": [{"title": "A"}, {"title": "B"}],
            "current_index": 0,
        })
        spy.assert_called()

    def test_operation_failed_does_not_emit_any(self):
        model, service = _make_model(
            [{"title": "A"}], current_index=0,
        )
        spy = MagicMock()
        model.countChanged.connect(spy)
        model.dataChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("operationFailed", {"error": "test"})
        spy.assert_not_called()

    def test_modes_changed_triggers_refresh(self):
        model, service = _make_model(
            [{"title": "A"}], current_index=0,
        )
        spy = MagicMock()
        model.countChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("modesChanged", {
            "operation": "set_repeat",
            "repeat": "all",
            "items": [{"title": "A"}],
            "current_index": 0,
        })
        spy.assert_called()

    def test_state_restored_triggers_refresh(self):
        model, service = _make_model([], current_index=-1)
        spy = MagicMock()
        model.countChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("stateRestored", {
            "operation": "restore",
            "items": [{"title": "Restored"}],
            "current_index": 0,
        })
        spy.assert_called()


class TestPreservation:
    """Verify non-structural changes don't cause full model reset.

    In QML, targeted dataChanged preserves ListView scroll position and
    keyboard focus, while beginResetModel/endResetModel destroys them.
    """

    def test_index_change_uses_data_changed_not_reset(self):
        """Index changes emit dataChanged, NOT beginResetModel."""
        model, service = _make_model(
            [{"title": "A"}, {"title": "B"}, {"title": "C"}],
            current_index=0,
        )
        # Track beginResetModel calls
        original_begin = model.beginResetModel
        reset_count = [0]
        def counting_begin():
            reset_count[0] += 1
            original_begin()
        model.beginResetModel = counting_begin

        handler = service.subscribe.call_args[0][0]
        handler("currentIndexChanged", {
            "operation": "next",
            "items": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
            "current_index": 1,
        })
        # Should NOT have called beginResetModel
        assert reset_count[0] == 0

    def test_structural_change_uses_reset(self):
        """Structural changes (add/remove/clear) use full refresh."""
        model, service = _make_model(
            [{"title": "A"}], current_index=0,
        )
        original_begin = model.beginResetModel
        reset_count = [0]
        def counting_begin():
            reset_count[0] += 1
            original_begin()
        model.beginResetModel = counting_begin

        handler = service.subscribe.call_args[0][0]
        handler("queueChanged", {
            "operation": "add",
            "items": [{"title": "A"}, {"title": "B"}],
            "current_index": 0,
        })
        # Should have called beginResetModel for structural change
        assert reset_count[0] == 1
