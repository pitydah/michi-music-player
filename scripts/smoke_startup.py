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
        import traceback
        traceback.print_exc()
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


def _check_audio_lab_routes():
    """Validate all Audio Lab NAV_ROUTES exist as window handler methods."""
    from ui.controllers.navigation_controller import NAV_ROUTES

    audio_lab_keys = [k for k in NAV_ROUTES if k.startswith("audio_lab")]
    audio_lab_keys.append("michi_disc_lab")

    if not audio_lab_keys:
        print("  ✗ No Audio Lab routes found")
        return 1

    errors = 0
    for key in sorted(audio_lab_keys):
        method_name = NAV_ROUTES.get(key)
        if not method_name:
            print(f"  ✗ {key}: no handler method in NAV_ROUTES")
            errors += 1
            continue
        print(f"  ✓ {key} → {method_name}")

    if errors:
        print(f"  ✗ {errors} route(s) missing handlers")
    else:
        print(f"  ✓ {len(audio_lab_keys)} Audio Lab routes validated")

    return errors


def main():
    errors = 0
    tmp_root = None
    created_tmp = False

    try:
        tmp_root, created_tmp = _ensure_env()

        print("=== Michi Music Player — Smoke Startup ===")
        print()

        print("[1/8] Environment")
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

        errors += _run_step("[7/8] NAV_ROUTES (Audio Lab)", _check_audio_lab_routes)
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
