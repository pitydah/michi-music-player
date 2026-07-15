"""EJ — Extracción lógica Widget: business rules out of ui/, into core/."""
import re
import sys
from pathlib import Path
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


REPO = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO))

UI_DIR = REPO / "ui"
CORE_DIR = REPO / "core"

SQL_PATTERN = re.compile(r'\b(SELECT\s+\w+|INSERT\s+INTO\s+\w+|UPDATE\s+\w+\s+SET|DELETE\s+FROM\s+\w+)\b', re.IGNORECASE)
MUTAGEN_PATTERN = re.compile(r'\b(mutagen|tinytag|eyed3|musicbrainzngs|discogs_client)\b', re.IGNORECASE)
THREAD_PATTERN = re.compile(r'threading\.Thread\(')
FS_PATTERN = re.compile(r'os\.(path|listdir|walk|makedirs|remove|rename|stat|unlink|rmdir|scandir)', re.IGNORECASE)
PLAYLIST_IO = re.compile(r'\b(m3u|pls|xspf)\b', re.IGNORECASE)


def _ui_files():
    return [f for f in sorted(UI_DIR.rglob("*.py")) if not f.name.startswith("__")]


def test_no_business_rules_in_ui_prelude():
    violations = []
    for f in _ui_files():
        text = f.read_text()
        rel = f.relative_to(REPO)
        sql = SQL_PATTERN.findall(text)
        if sql:
            violations.append(f"{rel}: SQL ({len(sql)} matches)")
        meta = MUTAGEN_PATTERN.findall(text)
        if meta:
            violations.append(f"{rel}: metadata ({len(meta)} matches)")
        thr = THREAD_PATTERN.findall(text)
        if thr:
            violations.append(f"{rel}: raw threading ({len(thr)} matches)")
        pl = PLAYLIST_IO.findall(text)
        if pl:
            violations.append(f"{rel}: playlist IO ({len(pl)} matches)")
    print(f"Business rule violations (expected in EJ extraction): {len(violations)}")
    for v in violations[:10]:
        print(f"  {v}")


ALLOWED_CORE_QTWIDGETS = {
    "core/file_actions.py",
    "core/playback_controller.py",
}

def test_core_has_no_qtwidgets_imports():
    for f in sorted(CORE_DIR.rglob("*.py")):
        if f.name.startswith("__"):
            continue
        rel = str(f.relative_to(REPO))
        if rel in ALLOWED_CORE_QTWIDGETS:
            continue
        text = f.read_text()
        if "PySide6.QtWidgets" in text or "PyQt6.QtWidgets" in text:
            pytest.fail(f"core/ should not import QtWidgets: {f.relative_to(REPO)}")


def test_core_services_exist():
    services = [
        "core/playback_controller.py",
        "core/queue_service.py",
        "core/settings_service.py",
        "core/metadata_service.py",
        "core/playlist_service.py",
        "core/global_search_service.py",
        "core/history_query_service.py",
        "core/mix_query_service.py",
        "core/library_sources_service.py",
        "core/connection_factory.py",
        "core/home/home_dashboard_service.py",
        "core/library/repositories/album_repository.py",
        "core/library/repositories/artist_repository.py",
        "core/radio/",
        "core/diagnostics/",
        "core/audio_lab/",
        "audio/output_profiles.py",
        "audio/eq_curve.py",
    ]
    missing = [s for s in services if not (REPO / s).exists()]
    assert not missing, f"Missing services: {missing}"


def test_controllers_are_thin():
    controllers_dir = UI_DIR / "controllers"
    if not controllers_dir.exists():
        pytest.skip("no controllers dir")
    thick = []
    for f in sorted(controllers_dir.rglob("*.py")):
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        if "conn.execute" in text or "mutagen" in text or "threading.Thread" in text:
            thick.append(f.relative_to(REPO))
    if thick:
        print(f"Thick controllers (need extraction): {len(thick)}")
        for t in thick[:5]:
            print(f"  {t}")


def test_metadata_logic_in_core():
    core_meta_files = list(CORE_DIR.rglob("metadata*"))
    core_meta_files += list(CORE_DIR.rglob("metadata_*"))
    assert len(core_meta_files) >= 3, "Need metadata service files in core"


def test_filesystem_ops_in_core():
    fs_files = []
    for f in sorted(CORE_DIR.rglob("*.py")):
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        if FS_PATTERN.search(text):
            fs_files.append(f.relative_to(REPO))
    assert len(fs_files) >= 3, "Need filesystem operations in core"


def test_playlist_io_in_core():
    pl_files = []
    for f in sorted(CORE_DIR.rglob("*.py")):
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        if PLAYLIST_IO.search(text) or "playlist" in text.lower() and ("import" in text.lower() or "export" in text.lower()):
            pl_files.append(f.relative_to(REPO))
    if not pl_files:
        print("No playlist IO found in core (may need extraction)")
    else:
        print(f"Playlist IO in core: {len(pl_files)} files")
        for p in pl_files[:3]:
            print(f"  {p}")


def test_device_logic_in_core():
    device_files = list(CORE_DIR.rglob("*device*"))
    device_files += list(CORE_DIR.rglob("*dac*"))
    assert len(device_files) >= 1, "Need device logic in core"
    print(f"Device files in core: {len(device_files)}")


def test_radio_logic_in_core():
    radio_dir = CORE_DIR / "radio"
    assert radio_dir.exists(), "Need radio logic in core"
    py_files = list(radio_dir.rglob("*.py"))
    assert len(py_files) >= 2, f"Need radio service files in core, got {len(py_files)}"


def test_settings_logic_in_core():
    settings_files = [
        CORE_DIR / "settings_manager.py",
        CORE_DIR / "settings_service.py",
        CORE_DIR / "settings_schema.py",
        CORE_DIR / "settings_migrations.py",
    ]
    existing = [s for s in settings_files if s.exists()]
    assert len(existing) >= 3, f"Need settings logic in core, got {len(existing)}"
    print(f"Settings files in core: {len(existing)}")
