from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QSignalSpy

from ui_qml_bridge.route_registry import ROUTES, ROUTE_ALIASES, resolve_route


REPO_ROOT = Path(__file__).resolve().parents[3]
QML_ROOT = REPO_ROOT / "ui_qml"
COMPONENTS = QML_ROOT / "components"


@pytest.fixture
def qml_engine(qapp) -> QQmlEngine:
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_ROOT))
    return engine


def _create_component(engine: QQmlEngine, name: str) -> tuple[QQmlComponent, QObject]:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(COMPONENTS / name)))
    assert component.isReady(), [error.toString() for error in component.errors()]
    instance = component.create()
    assert instance is not None, [error.toString() for error in component.errors()]
    return component, instance


def test_canonical_playback_components_exist() -> None:
    expected = {
        "PlaybackTransport.qml",
        "PlaybackProgress.qml",
        "OutputProfileMenu.qml",
    }

    assert {path.name for path in COMPONENTS.glob("*.qml")} >= expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "0:00"), (65, "1:05"), (3605, "60:05")],
)
def test_playback_progress_formats_time(
    qml_engine: QQmlEngine, seconds: int, expected: str
) -> None:
    component, progress = _create_component(qml_engine, "PlaybackProgress.qml")

    assert progress.formatTime(seconds) == expected

    progress.deleteLater()
    component.deleteLater()


def test_playback_transport_emits_play_and_pause_requests(qml_engine: QQmlEngine) -> None:
    component, transport = _create_component(qml_engine, "PlaybackTransport.qml")
    button = transport.findChild(QObject, "nowPlayingPlayPauseButton")
    play_spy = QSignalSpy(transport.playRequested)
    pause_spy = QSignalSpy(transport.pauseRequested)

    assert button is not None, "Could not find nowPlayingPlayPauseButton"
    transport.setProperty("isPlaying", False)
    button.click()
    transport.setProperty("isPlaying", True)
    button.click()

    assert play_spy.count() == 1
    assert pause_spy.count() == 1

    transport.deleteLater()
    component.deleteLater()


def test_playback_transport_cycles_repeat_modes(qml_engine: QQmlEngine) -> None:
    component, transport = _create_component(qml_engine, "PlaybackTransport.qml")
    button = transport.findChild(QObject, "nowPlayingRepeatButton")
    repeat_spy = QSignalSpy(transport.repeatCycled)

    assert button is not None, "Could not find nowPlayingRepeatButton"
    for mode in ("none", "all", "one"):
        transport.setProperty("repeatMode", mode)
        button.click()

    assert [repeat_spy.at(index)[0] for index in range(repeat_spy.count())] == [
        "all",
        "one",
        "none",
    ]

    transport.deleteLater()
    component.deleteLater()


def test_nowplaying_surfaces_use_canonical_playback_components() -> None:
    bar = (COMPONENTS / "NowPlayingBar.qml").read_text(encoding="utf-8")
    page = (QML_ROOT / "pages" / "nowplaying" / "NowPlayingPage.qml").read_text(
        encoding="utf-8"
    )

    # Now bar uses PlaybackTransport (variant: "bar") in both desktop and compact
    bar_transports = bar.count("PlaybackTransport {")
    assert bar_transports >= 1, "NowPlayingBar should contain at least one PlaybackTransport"
    assert "variant: \"bar\"" in bar
    assert "OutputProfileMenu {" in bar
    assert "AudioOutputMenu {" in bar
    assert "PlaybackTransport {" in page
    # PlaybackPage no longer exists
    import pathlib
    assert not pathlib.Path("ui_qml/pages/PlaybackPage.qml").exists()


def test_playback_route_converges_on_nowplaying() -> None:
    nowplaying = ROUTES["nowplaying"]

    # "playback" is no longer a standalone route; it is a legacy alias of the
    # canonical "nowplaying" route and must resolve to the same source page.
    assert "playback" not in ROUTES
    assert ROUTE_ALIASES["playback"] == "nowplaying"
    assert resolve_route("playback") == "nowplaying"
    assert ROUTES[resolve_route("playback")]["source"] == nowplaying["source"]


def test_obsolete_nowplaying_components_are_removed() -> None:
    obsolete = {
        "ExpandedNowPlayingPanel.qml",
        "NowPlayingControls.qml",
        "NowPlayingCover.qml",
        "NowPlayingInfo.qml",
        "NowPlayingQualityBadge.qml",
        "NowPlayingQueuePanel.qml",
        "NowPlayingSeekBar.qml",
        "NowPlayingTransport.qml",
    }

    assert not ({path.name for path in COMPONENTS.glob("*.qml")} & obsolete)
    assert not (QML_ROOT / "pages" / "nowplaying" / "NowPlayingControls.qml").exists()
    assert not (QML_ROOT / "pages" / "nowplaying" / "NowPlayingProgress.qml").exists()


def test_qml_surfaces_do_not_reference_removed_components() -> None:
    removed_types = {
        "NowPlayingControls",
        "NowPlayingProgress",
        "NowPlayingSeekBar",
        "NowPlayingTransport",
    }
    stale_references = []

    for path in QML_ROOT.rglob("*.qml"):
        content = path.read_text(encoding="utf-8")
        for removed_type in removed_types:
            if f"{removed_type} {{" in content:
                stale_references.append(f"{path.relative_to(QML_ROOT)}: {removed_type}")

    assert stale_references == []
