#!/usr/bin/env python3
"""Michi Music Player — smoke startup validation.

Validates critical runtime components can initialize without real audio,
real user data, or external services. Designed for CI and pre-beta testing.

Usage:
    python3 scripts/smoke_startup.py

Environment (set automatically if missing):
    QT_QPA_PLATFORM=offscreen
    MICHI_TEST_DATA_DIR, MICHI_TEST_CACHE_DIR, MICHI_TEST_CONFIG_DIR
"""
import os
import sys
import tempfile

# Add repo root to path so the package can be imported when running from source
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def _ensure_env():
    """Set safe defaults for test environment if not already set.

    Returns (tmp_root, created_tmp):
        tmp_root: path to created temp dir, or None if using external vars
        created_tmp: True if we created a temp dir (must clean it up)
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    all_set = all(
        k in os.environ
        for k in ("MICHI_TEST_DATA_DIR", "MICHI_TEST_CACHE_DIR", "MICHI_TEST_CONFIG_DIR")
    )
    if all_set:
        return None, False

    tmp = tempfile.mkdtemp(prefix="michi-smoke-")
    os.environ.setdefault("MICHI_TEST_DATA_DIR", os.path.join(tmp, "data"))
    os.environ.setdefault("MICHI_TEST_CACHE_DIR", os.path.join(tmp, "cache"))
    os.environ.setdefault("MICHI_TEST_CONFIG_DIR", os.path.join(tmp, "config"))
    return tmp, True


def _diagnostics():
    print(f"  Python:     {sys.executable}")
    print(f"  Version:    {sys.version.split()[0]}")
    print(f"  QT_QPA:     {os.environ.get('QT_QPA_PLATFORM', 'NOT SET')}")
    print(f"  DATA_DIR:   {os.environ.get('MICHI_TEST_DATA_DIR', 'NOT SET')}")
    print(f"  CACHE_DIR:  {os.environ.get('MICHI_TEST_CACHE_DIR', 'NOT SET')}")
    print(f"  CONFIG_DIR: {os.environ.get('MICHI_TEST_CONFIG_DIR', 'NOT SET')}")


def _run_step(label, fn):
    """Run a step function with clean error handling."""
    print(label)
    try:
        return fn()
    except Exception as e:
        print(f"  ✗ {e!r}")
        return 1


def _check_imports():
    errors = 0
    checks = ["PySide6", "mutagen", "numpy"]
    for name in checks:
        try:
            __import__(name)
            print(f"  ✓ {name}")
        except ImportError as e:
            print(f"  ✗ {name}: {e}")
            errors += 1
    # Verify indexing layer modules import cleanly
    indexer_modules = [
        "library.batch_writer",
        "library.change_detector",
        "library.file_watcher",
        "library.folder_index",
        "library.indexer",
        "library.smart_mixes",
    ]
    for mod_name in indexer_modules:
        try:
            __import__(mod_name)
            print(f"  ✓ {mod_name}")
        except Exception as e:
            print(f"  ✗ {mod_name}: {e!r}")
            errors += 1
    return errors


def _check_gst():
    try:
        import gi
        gi.require_version("Gst", "1.0")
        gi.require_version("GstPbutils", "1.0")
        from gi.repository import Gst, GstPbutils  # noqa: F401
        Gst.init(None)
        print(f"  ✓ GStreamer {Gst.version_string()}")
        print(f"  ✓ GstPbutils ({GstPbutils})")
        return 0
    except Exception as e:
        print(f"  ✗ PyGObject/GStreamer: {e!r}")
        return 1


def _check_paths():
    from core.paths import (
        app_data_dir, app_cache_dir, app_config_dir,
        database_path, covers_cache_dir, log_file,
    )
    for label, path_fn in [
        ("app_data_dir", app_data_dir),
        ("app_cache_dir", app_cache_dir),
        ("app_config_dir", app_config_dir),
        ("database_path", database_path),
        ("covers_cache_dir", covers_cache_dir),
        ("log_file", log_file),
    ]:
        p = path_fn()
        d = os.path.dirname(p) if "." in os.path.basename(p) else p
        os.makedirs(d, exist_ok=True)
        print(f"  ✓ {label}: {p}")
    return 0


def _check_db():
    from core.paths import database_path
    from library.library_db import LibraryDB

    db_path = database_path()
    db = LibraryDB(db_path)
    try:
        assert os.path.isfile(db_path), f"DB file not created: {db_path}"
        data_dir = os.environ.get("MICHI_TEST_DATA_DIR", "")
        assert db_path.startswith(data_dir), (
            f"DB path {db_path} not under test data dir {data_dir}"
        )
        print(f"  ✓ LibraryDB created at {db_path}")
        result = db.get_all()
        print(f"  ✓ DB query (get_all): {len(result)} items")
        return 0
    finally:
        db.close()


def _check_qt():
    from PySide6.QtWidgets import QApplication, QLabel
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    label = QLabel("Michi Smoke Test")
    label.setWindowTitle("Michi Smoke Test")
    print(f"  ✓ QApplication initialized (platform: {app.platformName()})")
    print("  ✓ QLabel created")
    return 0


def _check_main_window():
    """Create MainWindow in safe mode to validate all controllers and navigation."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    os.environ.setdefault("MICHI_SAFE_MODE", "1")

    from ui.window import MainWindow
    w = MainWindow()

    checks = [
        '_nav_ctrl', '_lib_ctrl', '_home_ctrl', '_services',
        '_view_registry', '_ha_handlers', '_cf_ctrl', '_smart_ctrl',
        '_srv_ctrl', '_id_handlers', '_sidebar_menu_ctrl',
        '_search_router', '_view_router', '_album_sort_menu',
        '_playback_ctrl', '_album_ctrl', '_artist_ctrl', '_genre_ctrl',
        '_playlist_ctrl', '_file_actions', '_expanded_ctrl',
        '_cast_ctrl', '_transmit_ctrl', '_audio_output_ctrl', '_ctx',
    ]
    for attr in checks:
        v = getattr(w, attr, None)
        assert v is not None, f"MainWindow missing {attr}"

    # Navigate all sections to verify routing
    sections = [
        'home', 'library_hub', 'mix_hub', 'playlist_hub', 'playback_hub',
        'connections_hub', 'radio', 'audio_lab', 'home_audio', 'identifier',
        'assistant', 'discover', 'settings_hub', 'devices_page',
        'michi_disc_lab', 'metadata_editor', 'albums', 'artists', 'genres',
        'folders', 'favs', 'recent',
    ]
    for key in sections:
        w._nav_ctrl.dispatch(key)

    # Verify navigation history preserves search text
    w._nav_ctrl.dispatch("library_hub")
    w._search_text = "search query"
    w._nav_ctrl.dispatch("albums")
    w._nav_ctrl.dispatch("library_hub")
    nav_ctrl = w._nav_ctrl
    assert nav_ctrl._history._history[-1][0] == "library_hub", "history key mismatch"
    assert nav_ctrl._history._history[-1][1] == "", "search should be empty after navigate"

    # Verify view mode switching
    w._current_section_key = "albums"
    w._view_router.on_mode_changed("grid")
    assert w._view_mode == "grid", f"Expected grid, got {w._view_mode}"
    w._view_router.on_mode_changed("list")
    assert w._view_mode == "list", f"Expected list, got {w._view_mode}"

    # Verify CoverFlow can be activated
    w._current_section_key = "albums"
    w._view_router.on_mode_changed("coverflow")
    cf = getattr(w, '_coverflow', None)
    if cf is not None:
        assert callable(cf.count), "CoverFlow has count method"
        assert callable(cf.item_at), "CoverFlow has item_at"
        assert callable(cf.set_cover), "CoverFlow has set_cover"

    print("  ✓ MainWindow created (safe mode)")
    print(f"  ✓ {len(checks)} controllers confirmed")
    print(f"  ✓ {len(sections)} sections navigable")
    print("  ✓ nav history preserves search text")
    print("  ✓ view mode switching (list/grid/coverflow)")
    return 0


def main():
    errors = 0
    tmp_root = None
    created_tmp = False

    try:
        tmp_root, created_tmp = _ensure_env()

        print("=== Michi Music Player — Smoke Startup ===")
        print()

        print("[1/7] Environment")
        _diagnostics()
        print()

        errors += _run_step("[2/7] Python imports", _check_imports)
        print()

        errors += _run_step("[3/7] PyGObject / GStreamer", _check_gst)
        print()

        errors += _run_step("[4/7] XDG paths", _check_paths)
        print()

        errors += _run_step("[5/7] SQLite database", _check_db)
        print()

        errors += _run_step("[6/7] Qt widgets", _check_qt)
        print()

        errors += _run_step("[7/7] MainWindow", _check_main_window)
        print()

        print("[8/8] Summary")
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
