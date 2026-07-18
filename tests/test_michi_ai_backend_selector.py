"""Test backend selector fallback and availability."""
from __future__ import annotations

from core.ai.backend_selector import BackendSelector
from core.ai.backends.calico import CalicoBackend


def test_default_backend_is_calico():
    sel = BackendSelector()
    be = sel.active
    assert isinstance(be, CalicoBackend)


def test_calico_always_available():
    sel = BackendSelector()
    avail = sel.available_backends()
    assert avail.get("calico") is True


def test_gguf_backends_not_available_without_model():
    sel = BackendSelector()
    avail = sel.available_backends()
    assert avail.get("munchkin") is False
    assert avail.get("carey") is False
    assert avail.get("maine_coon") is False


def test_auto_fallback_to_calico_when_none_available(monkeypatch):
    sel = BackendSelector()
    monkeypatch.setattr("core.ai.backends.sphynx.SphynxBackend.is_available", lambda self: False)
    be = sel.auto_fallback()
    assert isinstance(be, CalicoBackend)


def test_set_active_to_calico():
    sel = BackendSelector()
    sel.set_active("calico")
    assert isinstance(sel.active, CalicoBackend)


def test_set_active_to_unknown_falls_back_to_calico():
    sel = BackendSelector()
    sel.set_active("nonexistent")
    assert isinstance(sel.active, CalicoBackend)


def test_get_backend_returns_none_for_unknown():
    sel = BackendSelector()
    assert sel.get_backend("nonexistent") is None
