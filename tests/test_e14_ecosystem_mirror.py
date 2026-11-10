"""E14 M11: Ecosystem QML mirror and UI boundary checks."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src/michi/presentation/qml/ecosystem"
MIRROR = ROOT / "src/michi_ecosystem/qml/ecosystem"
SCRIPT = ROOT / "scripts/verify_ecosystem_qml_mirror.py"


def _module():
    spec = importlib.util.spec_from_file_location("ecosystem_qml_mirror", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_qml(root: Path, name: str, body: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_repository_qml_mirror_is_exact() -> None:
    module = _module()
    assert module.inventory(CANONICAL).keys() == module.inventory(MIRROR).keys()
    assert module.compare(CANONICAL, MIRROR) == []


def test_mirror_detects_changed_missing_and_extra_files(tmp_path: Path) -> None:
    module = _module()
    canonical = tmp_path / "canonical"
    mirror = tmp_path / "mirror"
    _write_qml(canonical, "Page.qml", "Item {}\n")
    _write_qml(canonical, "detail/Detail.qml", "Item {}\n")
    _write_qml(mirror, "Page.qml", "Item { id: root }\n")

    problems = module.compare(canonical, mirror)
    assert "content differs: Page.qml" in problems
    assert "missing from mirror: detail/Detail.qml" in problems

    _write_qml(mirror, "extra/Extra.qml", "Item {}\n")
    assert "unexpected in mirror: extra/Extra.qml" in module.compare(canonical, mirror)


def test_sync_repairs_the_package_mirror(tmp_path: Path) -> None:
    module = _module()
    canonical = tmp_path / "canonical"
    mirror = tmp_path / "mirror"
    _write_qml(canonical, "Page.qml", "Item {}\n")
    _write_qml(mirror, "stale/Stale.qml", "Item {}\n")

    module.synchronize(canonical, mirror)
    assert module.compare(canonical, mirror) == []
    assert not (mirror / "stale/Stale.qml").exists()


def test_ecosystem_qml_contains_no_player_playback_authority() -> None:
    forbidden = (
        "NowPlayingBar",
        "PlaybackBridge",
        "QueueBridge",
        "AudioEngineBridge",
        "playbackBridge",
        "audioEngine",
        "queueBridge",
        "MediaPlayer",
    )
    offenders: list[str] = []
    for path in CANONICAL.rglob("*.qml"):
        source = path.read_text(encoding="utf-8")
        offenders.extend(
            f"{path.relative_to(ROOT)}: {name}" for name in forbidden if name in source
        )
    assert offenders == []


def test_manual_discovery_surface_has_no_timer_polling() -> None:
    page = (CANONICAL / "discovery/DiscoveryPage.qml").read_text(encoding="utf-8")
    assert "Buscar ahora" in page
    assert "Detener búsqueda" in page
    assert "startDiscovery()" in page
    assert "stopDiscovery()" in page
    assert "discoveryStateLabel" in page
    assert "Timer {" not in page
    assert "poll(" not in page
