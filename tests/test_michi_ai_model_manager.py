"""Test ModelManager lifecycle (without actual model downloads)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.ai.model_manager import ModelManager


def test_model_manager_creates_storage():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        assert Path(tmp).exists()


def test_model_status_not_installed_initially():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        status = mm.get_status("munchkin")
        assert status == "not_installed"


def test_get_all_status_returns_dict():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        statuses = mm.get_all_status()
        assert isinstance(statuses, dict)


def test_is_installed_returns_false_initially():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        assert mm.is_installed("carey") is False


def test_is_loaded_returns_false_initially():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        assert mm.is_loaded("munchkin") is False


def test_get_storage_path():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        path = mm.get_storage_path()
        assert path == Path(tmp)


def test_get_installed_models_empty_initially():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        assert mm.get_installed_models() == []


def test_delete_nonexistent_model_does_not_raise():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        mm.delete("nonexistent")


def test_get_runtime_stats_for_unloaded_model():
    with tempfile.TemporaryDirectory() as tmp:
        mm = ModelManager(storage_dir=tmp)
        stats = mm.get_runtime_stats("munchkin")
        assert stats.get("loaded") is False
        assert stats.get("ram_mb") == 0
