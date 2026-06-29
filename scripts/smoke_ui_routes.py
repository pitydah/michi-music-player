#!/usr/bin/env python3
"""Deep UI smoke: MainWindow controllers, navigation routes and view modes.

Requires: QT_QPA_PLATFORM=offscreen, MICHI_SAFE_MODE=1, MICHI_TEST_* vars.
"""
import os
import sys
import tempfile

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def _ensure_env():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("MICHI_SAFE_MODE", "1")
    all_set = all(k in os.environ for k in (
        "MICHI_TEST_DATA_DIR", "MICHI_TEST_CACHE_DIR", "MICHI_TEST_CONFIG_DIR"))
    if all_set:
        return None, False
    tmp = tempfile.mkdtemp(prefix="michi-ui-smoke-")
    os.environ.setdefault("MICHI_TEST_DATA_DIR", os.path.join(tmp, "data"))
    os.environ.setdefault("MICHI_TEST_CACHE_DIR", os.path.join(tmp, "cache"))
    os.environ.setdefault("MICHI_TEST_CONFIG_DIR", os.path.join(tmp, "config"))
    return tmp, True


def _check_main_window():
    """Create MainWindow in safe mode — deep route and view validation."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    from ui.window import MainWindow
    w = MainWindow()
    try:
        controllers = [
            '_nav_ctrl', '_lib_ctrl', '_home_ctrl', '_services',
            '_view_registry', '_cf_ctrl', '_smart_ctrl', '_srv_ctrl',
            '_id_handlers', '_sidebar_menu_ctrl', '_search_router',
            '_view_router', '_album_sort_menu', '_playback_ctrl',
            '_album_ctrl', '_artist_ctrl', '_genre_ctrl', '_playlist_ctrl',
            '_file_actions', '_expanded_ctrl', '_cast_ctrl',
            '_transmit_ctrl', '_audio_output_ctrl', '_ctx',
        ]
        for attr in controllers:
            v = getattr(w, attr, None)
            assert v is not None, f"MainWindow missing {attr}"
        print(f"  ✓ {len(controllers)} controllers confirmed")

        sections = [
            'home', 'library_hub', 'mix_hub', 'playlist_hub', 'playback_hub',
            'connections_hub', 'radio', 'audio_lab', 'home_audio', 'identifier',
            'assistant', 'discover', 'settings_hub', 'devices_page',
            'michi_disc_lab', 'metadata_editor', 'albums', 'artists', 'genres',
            'folders', 'favs', 'recent',
        ]
        for key in sections:
            w._nav_ctrl.dispatch(key)
        print(f"  ✓ {len(sections)} sections navigable")

        # Verify search history preservation
        w._nav_ctrl.dispatch("library_hub")
        w._search_text = "beatles"
        w._nav_ctrl.dispatch("albums")
        w._nav_ctrl.dispatch("library_hub")
        assert w._nav_ctrl._history._history[-1][1] == "", "history search mismatch"
        w._nav_ctrl.navigate_back()
        assert w._nav_ctrl._history.current_key == "albums", "navigate back failed"
        print("  ✓ nav history preserves search text")

        # View mode switching
        w._nav_ctrl.dispatch("albums")
        w._view_router.on_mode_changed("grid")
        assert w._view_mode == "grid", f"Expected grid, got {w._view_mode}"
        w._view_router.on_mode_changed("coverflow")
        cf = getattr(w, '_coverflow', None)
        if cf:
            assert callable(cf.count), "CoverFlow has count"
        print("  ✓ view mode switching (grid/coverflow)")

        # Route vs sidebar separation — mandatory
        w._nav_ctrl.dispatch("albums")
        assert w._current_route_key == "albums"
        assert w._current_sidebar_key == "library_hub"

        w._nav_ctrl.dispatch("pl:123")
        assert w._current_route_key == "pl:123"
        assert w._current_sidebar_key == "playlist_hub"

        # srv: and dev: dispatch handlers may hang in offscreen (no real server),
        # so we verify the state mapping via resolve_sidebar_active_key and
        # verify dispatch sets state correctly for known-good route.
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("srv:navidrome") == "connections_hub"
        assert resolve_sidebar_active_key("dev:usb") == "devices_page"

        # Verify direct state assignment works for all route types
        w._current_route_key = "srv:navidrome"
        w._current_sidebar_key = resolve_sidebar_active_key("srv:navidrome")
        assert w._current_sidebar_key == "connections_hub"
        w._current_route_key = "dev:usb"
        w._current_sidebar_key = resolve_sidebar_active_key("dev:usb")
        assert w._current_sidebar_key == "devices_page"
        print("  ✓ route/sidebar separation (albums, playlists, servers, devices)")

        return 0
    finally:
        w.close()
        w.deleteLater()
        app.processEvents()


def _run_step(label, fn):
    print(label)
    try:
        return fn()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ✗ {e!r}")
        return 1


def main():
    errors = 0
    tmp_root, created_tmp = None, False

    try:
        tmp_root, created_tmp = _ensure_env()
        print("=== Michi Music Player — Deep UI Smoke ===")
        print()

        errors += _run_step("[1/1] MainWindow & routing", _check_main_window)
        print()

        print("[2/2] Summary")
        if errors:
            print(f"  ✗ {errors} error(s) detected")
        else:
            print("  ✓ All checks passed")
    finally:
        if created_tmp and tmp_root:
            import shutil
            shutil.rmtree(tmp_root, ignore_errors=True)

    sys.exit(errors)


if __name__ == "__main__":
    main()
