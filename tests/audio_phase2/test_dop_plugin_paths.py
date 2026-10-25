"""Canonical DoP plugin location contract (Gate A root vs installed dir)."""

from __future__ import annotations

import pytest

from michi.infrastructure.audio_output.dop_plugin import (
    resolve_dop_manifest_path,
    resolve_dop_plugin_path,
    resolve_dop_prefix,
)


def _write_plugin(directory):
    directory.mkdir(parents=True)
    (directory / "libmichidop.so").write_bytes(b"plugin")
    (directory / "michidop.manifest.json").write_text("{}", encoding="utf-8")
    return directory


def test_gate_a_root_and_installed_directory_resolve_to_same_prefix(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "gate-a"
    installed = _write_plugin(root / "lib/gstreamer-1.0")
    monkeypatch.setenv("MICHI_DOP_PREFIX", str(root))
    assert resolve_dop_prefix() == installed.resolve()
    assert resolve_dop_plugin_path() == (installed / "libmichidop.so").resolve()
    assert (
        resolve_dop_manifest_path() == (installed / "michidop.manifest.json").resolve()
    )

    monkeypatch.delenv("MICHI_DOP_PREFIX")
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(installed))
    assert resolve_dop_prefix() == installed.resolve()


def test_explicit_incomplete_prefix_never_falls_back(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(tmp_path))
    with pytest.raises(RuntimeError, match="DOP_RUNTIME_UNAVAILABLE"):
        resolve_dop_prefix()


def test_incomplete_manifest_is_not_a_plugin(monkeypatch, tmp_path) -> None:
    directory = tmp_path / "plugin"
    directory.mkdir()
    (directory / "libmichidop.so").write_bytes(b"plugin")
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(directory))
    with pytest.raises(RuntimeError, match="DOP_RUNTIME_UNAVAILABLE"):
        resolve_dop_prefix()
