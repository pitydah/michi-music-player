"""Test that the unified MichiAIEngine works correctly."""
from __future__ import annotations

from core.ai_engine import MichiAIEngine


def test_engine_creates_with_defaults():
    engine = MichiAIEngine()
    assert engine is not None
    assert engine.backend_selector is not None


def test_engine_process_message_returns_dict():
    engine = MichiAIEngine()
    result = engine.process_message("hola")
    assert isinstance(result, dict)
    assert "ok" in result
    assert "response" in result
    assert "intent" in result
    assert "risk_level" in result
    assert "backend" in result


def test_engine_cancel_does_not_raise():
    engine = MichiAIEngine()
    engine.cancel()


def test_engine_set_active_backend():
    engine = MichiAIEngine()
    engine.set_active_backend("calico")
    be = engine.active_backend
    assert be is not None


def test_engine_get_suggestions():
    engine = MichiAIEngine()
    suggestions = engine.get_suggestions()
    assert isinstance(suggestions, list)
    if suggestions:
        assert "title" in suggestions[0]


def test_engine_backend_property():
    engine = MichiAIEngine()
    assert hasattr(engine, "active_backend")
    assert hasattr(engine, "backend_selector")


def test_engine_tool_registry_property():
    engine = MichiAIEngine()
    assert engine.tool_registry is not None
