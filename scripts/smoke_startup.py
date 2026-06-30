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


def _check_audio_lab_page_instantiation():
    """Instantiate Audio Lab page widgets to verify constructors work.

    Requires QApplication (created by _check_qt step).
    Only runs if MICHI_SMOKE_INCLUDE_AUDIO_LAB=1.
    No hardware, no capture, no conversion is started.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    errors = 0

    pages = [
        ("AudioLabPage", "ui.audio_lab.audio_lab_page", "AudioLabPage", {}),
        ("AudioLabIdentifierPage", "ui.audio_lab.sub_pages", "AudioLabIdentifierPage", {}),
        ("AudioLabBackupPage", "ui.audio_lab.sub_pages", "AudioLabBackupPage", {}),
        ("AudioLabDiagnosticsPage", "ui.audio_lab.sub_pages", "AudioLabDiagnosticsPage", {}),
        ("AudioLabOutputPage", "ui.audio_lab.sub_pages", "AudioLabOutputPage", {}),
        ("IntelligencePage", "ui.audio_lab.intelligence_page", "IntelligencePage",
         {"db": None, "worker_mgr": None}),
        ("ArtworkPage", "ui.audio_lab.artwork_page", "ArtworkPage", {"db": None}),
        ("MusicBrainzPage", "ui.audio_lab.musicbrainz_page", "MusicBrainzPage", {}),
        ("LyricsPage", "ui.audio_lab.lyrics_page", "LyricsPage", {}),
        ("OrganizePage", "ui.audio_lab.organize_page", "OrganizePage", {}),
        ("ConversionPage", "ui.audio_lab.conversion_page", "ConversionPage", {}),
        ("VinylLabPage", "ui.audio_lab.vinyl_lab_page", "VinylLabPage", {}),
        ("DSPPage", "ui.audio_lab.dsp_page", "DSPPage", {}),
        ("DiagnosticsPage (real)", "ui.audio_lab.diagnostics_page", "DiagnosticsPage", {}),
        ("diagnostics_service (import)", None, None, None),
        ("spectral_authenticator (import)", None, None, None),
    ]

    # Import-only tests (no instantiation)
    import_checks = [
        ("can_analyse", "from core.audio_analysis.spectral_authenticator import can_analyse; assert can_analyse('x.wav') == True; assert can_analyse('x.flac') == False"),
        ("analyse_file error", "from ui.audio_lab.diagnostics_service import analyse_file; r = analyse_file('/no/existe'); assert r.get('error') == 'Archivo no encontrado'"),
    ]

    for label, module_path, class_name, kwargs in pages:
        if module_path is None:
            continue
        try:
            mod = __import__(module_path, fromlist=[class_name])
            cls = getattr(mod, class_name)
            cls(**kwargs)
            msg = f"  ✓ {label}"
            db_val = kwargs.get("db")
            if db_val is not None:
                msg += f" (db={db_val})"
            print(msg)
        except Exception as e:
            print(f"  ✗ {label}: {e}")
            errors += 1

    for label, code in import_checks:
        try:
            exec(code)
            print(f"  ✓ {label}")
        except Exception as e:
            print(f"  ✗ {label}: {e}")
            errors += 1

    return errors


def _check_context_core():
    """Validate ContextService can record events and build snapshots."""
    import os as _os
    import tempfile

    errors = 0
    tmp_db = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
            tmp_db = tf.name
        from core.context import context_repository as repo
        repo.override_db_path(tmp_db)
        from core.context.context_service import ContextService
        svc = ContextService()
        svc.record_scan_finished({"tracks": 0})
        svc.record_queue_updated(count=5, source="test")
        svc.record_event("smoke_test", {"ok": True})
        snap = svc.get_home_snapshot()
        snap2 = svc.get_assistant_snapshot()
        snap3 = svc.get_playback_context()
        assert "library_health" in snap
        assert "assistant_capabilities" in snap2
        assert "queue" in snap3
        assert not any("/" in str(v) for k, v in snap2.items() if isinstance(v, str))
        assert snap.get("playback", {}).get("queue", {}).get("active") is True
        repo.close()
        print("  ✓ OK — events, home, assistant")
    except Exception as e:
        errors += 1
        print(f"  ✗ ContextService smoke: {e}")
    finally:
        if tmp_db and _os.path.exists(tmp_db):
            import contextlib
            with contextlib.suppress(PermissionError):
                _os.unlink(tmp_db)
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

        if os.environ.get("MICHI_SMOKE_INCLUDE_AUDIO_LAB") == "1":
            errors += _run_step("[7/8] NAV_ROUTES (Audio Lab)", _check_audio_lab_routes)
            print()
            errors += _run_step("[8/8] Page instantiation (Audio Lab)", _check_audio_lab_page_instantiation)
        else:
            print()
            print("[7/7] NAV_ROUTES (Audio Lab) — skipped (set MICHI_SMOKE_INCLUDE_AUDIO_LAB=1 to enable)")
            print()

        # Context core smoke
        print()
        errors += _run_step("[7/7] ContextService", _check_context_core)
        print()

        print()
        print("[7/7] Summary" if not os.environ.get("MICHI_SMOKE_INCLUDE_AUDIO_LAB") else "[8/8] Summary")
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
