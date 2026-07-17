"""Tests that the Flatpak manifest references valid paths and dependencies."""

import shutil
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "packaging" / "flatpak" / "io.github.pitydah.michi-music-player.yml"


def _load_manifest():
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


class TestFlatpakManifestStructure:
    def test_manifest_exists(self):
        assert MANIFEST_PATH.is_file()

    def test_manifest_is_valid_yaml(self):
        manifest = _load_manifest()
        assert isinstance(manifest, dict)

    def test_required_keys(self):
        manifest = _load_manifest()
        assert "id" in manifest
        assert "runtime" in manifest
        assert "command" in manifest
        assert "modules" in manifest

    def test_app_id(self):
        manifest = _load_manifest()
        assert manifest["id"] == "io.github.pitydah.michi-music-player"

    def test_runtime_is_kde(self):
        manifest = _load_manifest()
        assert "kde" in manifest.get("runtime", "").lower()


class TestFlatpakBinaries:
    def test_command_is_installed(self):
        manifest = _load_manifest()
        cmd = manifest.get("command", "")
        assert cmd, "No command defined in manifest"
        found = shutil.which(cmd) is not None
        assert found, (
            f"Command '{cmd}' not found in PATH. "
            "This may be expected in CI; the test ensures the binary name is correct."
        )

    def test_python_is_available(self):
        assert shutil.which("python3") is not None


class TestFlatpakSources:
    def test_source_path_exists(self):
        manifest = _load_manifest()
        for module in manifest.get("modules", []):
            for source in module.get("sources", []):
                if source.get("type") == "dir":
                    path = source.get("path", "")
                    resolved = (MANIFEST_PATH.parent / path).resolve()
                    assert resolved.is_dir(), (
                        f"Source path '{path}' does not exist (resolved: {resolved})"
                    )


class TestFlatpakDesktopFile:
    def test_desktop_file_exists(self):
        manifest = _load_manifest()
        for module in manifest.get("modules", []):
            for cmd in module.get("build-commands", []):
                if "desktop" in cmd:
                    parts = cmd.split()
                    for p in parts:
                        if p.endswith(".desktop") and not p.startswith("/"):
                            desktop_path = REPO_ROOT / p
                            if desktop_path.is_file():
                                return
        pytest.skip("No desktop file path found in build-commands")

    def test_icon_exists(self):
        manifest = _load_manifest()
        for module in manifest.get("modules", []):
            for cmd in module.get("build-commands", []):
                if "icon" in cmd.lower() and ".png" in cmd:
                    parts = cmd.split()
                    for p in parts:
                        if p.endswith(".png") and not p.startswith("/"):
                            icon_path = REPO_ROOT / p
                            if icon_path.is_file():
                                return
        pytest.skip("No icon path found in build-commands")


class TestFlatpakFinishArgs:
    def test_wayland_socket(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "--socket=wayland" in args

    def test_x11_socket(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "--socket=x11" in args

    def test_pulseaudio_socket(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "--socket=pulseaudio" in args

    def test_network_share(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "--share=network" in args

    def test_music_filesystem(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "xdg-music" in args

    def test_avahi_dbus(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "Avahi" in args

    def test_mpris_own_name(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "mpris" in args.lower()

    def test_python_unbuffered(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "PYTHONUNBUFFERED=1" in args

    def test_dri_device(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "--device=dri" in args

    def test_ipc_share(self):
        manifest = _load_manifest()
        args = " ".join(manifest.get("finish-args", []))
        assert "--share=ipc" in args


class TestFlatpakQmlPaths:
    def test_ui_qml_directory_exists(self):
        assert (REPO_ROOT / "ui_qml").is_dir(), "ui_qml/ directory missing"

    def test_icons_directory_exists(self):
        assert (REPO_ROOT / "icons").is_dir(), "icons/ directory missing"

    def test_app_icon_used_in_manifest(self):
        manifest = _load_manifest()
        icon_name = manifest.get("rename-icon", "")
        assert icon_name, "rename-icon not set"
        assert icon_name == "michi-music-player"
