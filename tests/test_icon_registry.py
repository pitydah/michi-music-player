"""Tests for icon registry and loader."""
import os
from pathlib import Path
from legacy_widgets.ui_archive.icon_registry import ICON_REGISTRY, is_valid_ui_icon
from legacy_widgets.ui_archive.icon_loader import icon_path, validate_icon_key, app_icon

HERE = Path(__file__).parent.parent


class TestIconRegistry:
    def test_all_registered_icons_exist(self):
        missing = []
        for key, spec in ICON_REGISTRY.items():
            full = HERE / spec.path
            if not full.exists():
                missing.append(f"{key}: {full}")
        assert not missing, f"Missing icons: {missing}"

    def test_ui_icons_no_background(self):
        violations = []
        for key, spec in ICON_REGISTRY.items():
            if spec.family in ("sidebar", "action", "folder", "tray", "view") and spec.allow_background:
                violations.append(f"{key}: allow_background=True but family={spec.family}")
        assert not violations, f"Icons with background: {violations}"

    def test_no_absolute_paths(self):
        for key, spec in ICON_REGISTRY.items():
            assert not spec.path.startswith("/"), f"{key}: absolute path: {spec.path}"

    def test_icon_path_resolves_known(self):
        # Known icons should resolve
        for key in ["sidebar_library", "warm_play", "tray_icon", "home_audio"]:
            path = icon_path(key)
            assert path, f"{key}: no path resolved"
            assert os.path.exists(path), f"{key}: path not found: {path}"

    def test_app_icon_exists(self):
        path = app_icon()
        assert path, "app_icon: no path"
        assert os.path.exists(path), f"app_icon: not found: {path}"

    def test_validate_icon_key(self):
        assert validate_icon_key("sidebar_library")
        assert validate_icon_key("warm_play")
        assert not validate_icon_key("nonexistent_key")

    def test_is_valid_ui_icon(self):
        assert is_valid_ui_icon("sidebar_library")
        assert is_valid_ui_icon("warm_play")
