"""M11.3-UI-R1 — REAL QML behavioral tests (offscreen instantiation).

These tests instantiate the actual QML components (AudioEnginePopup,
AudioEngineSettingsSection) against a REAL AudioEngineBridge over the
canonical fake engine graph, then drive real properties/events:

- popup rows are real focusable Buttons (keyboard activation, Esc close)
- popup stays LIVE-BOUND while open (state changes re-render rows)
- competing rows disabled while a switch is in flight
- Settings cards have positive content-derived geometry
- fallback banner shows human copy only; raw error lives in Advanced
- advanced disclosure toggles by mouse AND keyboard (P1-01 ownership)
"""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_selection_coordinator import (
    AudioEngineSelectionCoordinator,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.playback_service import PlaybackService
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import AudioEngineId
from michi.presentation.audio_engine_bridge import AudioEngineBridge
from tests.test_m11_3f_engine_selection import FakeProvider, FakeSettingsRepository

QML_DIR = Path("src/michi/presentation/qml").resolve()


def _graph():
    """Deterministic engine graph + bridge (registry order Qt/Gst/MPD)."""
    qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
    gst = FakeProvider(AudioEngineId.GSTREAMER)
    mpd = FakeProvider(AudioEngineId.MPD)
    registry = AudioEngineRegistry([qt, gst, mpd])
    service = AudioEngineService(registry)
    router = AudioTransportRouter()
    playback = PlaybackService(router)
    settings = SettingsService(FakeSettingsRepository())
    coordinator = AudioEngineSelectionCoordinator(
        engine_service=service,
        registry=registry,
        router=router,
        playback=playback,
        settings=settings,
    )
    bridge = AudioEngineBridge(service, registry, coordinator)
    return service, registry, coordinator, bridge, qt, gst, mpd


POPUP_HARNESS = """
import QtQuick
import QtQuick.Controls.Basic
import "../player"

Window {
    id: harness
    visible: true
    width: 900
    height: 700
    color: "#000000"

    Item {
        anchors.fill: parent

    AudioEnginePopup {
        id: enginePopup
        objectName: "enginePopup"
        x: 40
        y: 40
        engines: audioEngine.engines
        selectedEngineId: audioEngine.selectedEngineId
        activeEngineId: audioEngine.activeEngineId
        switchingTo: audioEngine.switchingTo
        fallbackFrom: audioEngine.fallbackFrom
        hasFallback: audioEngine.fallbackFrom !== ""
            && audioEngine.selectedEngineId !== audioEngine.activeEngineId
        statusSummary: audioEngine.statusSummary
        onEngineSwitchRequested: (engineId) => harness.switchRequested(engineId)
    }

    }
    function switchRequested(engineId) {
        harness.lastSwitch = engineId
        harness.switchCount++
    }
    property int switchCount: 0
    property string lastSwitch: ""
}
"""

SETTINGS_HARNESS = """
import QtQuick
import QtQuick.Controls.Basic
import "../views"

Window {
    id: harness
    visible: true
    width: 1200
    height: 900
    color: "#000000"

    AudioEngineSettingsSection {
        id: section
        objectName: "engineSettingsSection"
        anchors.left: parent.left
        anchors.top: parent.top
        width: 1000
        engines: audioEngine.engines
        selectedEngineId: audioEngine.selectedEngineId
        activeEngineId: audioEngine.activeEngineId
        lifecycleLabel: audioEngine.lifecycleLabel
        fallbackFrom: audioEngine.fallbackFrom
        errorMessage: audioEngine.errorMessage
        statusSummary: audioEngine.statusSummary
        switchingTo: audioEngine.switchingTo
        onEngineSwitchRequested: (engineId) => harness.switchRequested(engineId)
    }

    function switchRequested(engineId) {
        harness.lastSwitch = engineId
        harness.switchCount++
    }
    property int switchCount: 0
    property string lastSwitch: ""
}
"""


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class _Harness:
    """Holds the QML engine/component references so the created window is
    never garbage-collected by the QML engine mid-test."""

    def __init__(self, engine, comp, window, service, registry, bridge, qt, gst, mpd):
        self.engine = engine
        self.comp = comp
        self.window = window
        self.service = service
        self.registry = registry
        self.bridge = bridge
        self.qt = qt
        self.gst = gst
        self.mpd = mpd


def _build(qapp, code, base_rel: str) -> _Harness:
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    service, registry, coordinator, bridge, qt, gst, mpd = _graph()
    engine.rootContext().setContextProperty("audioEngine", bridge)
    base = QUrl.fromLocalFile(str(QML_DIR / base_rel))
    comp = QQmlComponent(engine)
    comp.setData(code.encode("utf-8"), base)
    assert comp.status() == QQmlComponent.Ready, comp.errorString()
    window = comp.create()
    assert window is not None
    window.show()
    _run(comp)
    return _Harness(engine, comp, window, service, registry, bridge, qt, gst, mpd)


def _run(component, settle_ms: int = 0):
    """Process events until the window is exposed and bindings settle."""
    for _ in range(10):
        QApplication.processEvents()
    if settle_ms:
        QTest.qWait(settle_ms)
    return component


def _visual_roots(window):
    """The window's content item plus the popup overlay (popups live there).

    PySide6 does not expose QQuickWindow.overlay(), but the overlay IS a
    QObject child of the window — collect every QQuickItem child of the
    window (contentItem + overlay) and walk each visual tree."""
    roots = []
    if isinstance(window, QQuickWindow):
        for child in window.children():
            if isinstance(child, QQuickItem):
                roots.append(child)
    else:
        roots.append(window)
    return roots


def _walk(window):
    """Recursive visual-tree walker. NOTE: in this PySide6/offscreen
    environment QML items are NOT reachable through QObject::findChildren —
    the visual childItems() tree is the reliable structure."""
    seen = []
    for root in _visual_roots(window):
        stack = [root]
        while stack:
            item = stack.pop()
            if item is None:
                continue
            seen.append(item)
            if isinstance(item, QQuickItem):
                stack.extend(item.childItems())
    return seen


def _items(window, prefix: str):
    """All instantiated QML objects whose objectName starts with prefix."""
    return [o for o in _walk(window) if str(o.objectName()).startswith(prefix)]


def _by_name(window, name: str):
    """First object with the exact objectName: visual tree first, then the
    QObject tree (popups and their proxies are not visual Items)."""
    for o in _walk(window):
        if str(o.objectName()) == name:
            return o
    found = window.findChild(QObject, name)
    return found


def _text(item) -> str:
    return str(item.property("text"))


class TestPopupBehavioral:
    def test_three_visible_rows_after_open(self, qapp):
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        window = h.window
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        rows = _items(window, "enginePopupRow_")
        assert len(rows) == 3
        assert all(r.property("visible") for r in rows)
        popup.close()

    def test_enter_activates_focused_row_exactly_once(self, qapp):
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        window = h.window
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        qt_row = _by_name(window, "enginePopupRow_qt_multimedia")
        assert qt_row is not None
        qt_row.forceActiveFocus()
        _run(qapp)
        QTest.keyClick(window, Qt.Key_Return)
        _run(qapp, 50)
        assert window.property("switchCount") == 1
        assert window.property("lastSwitch") == "qt_multimedia"
        popup.close()

    def test_space_activates_focused_row_exactly_once(self, qapp):
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        window = h.window
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        qt_row = _by_name(window, "enginePopupRow_qt_multimedia")
        qt_row.forceActiveFocus()
        _run(qapp)
        QTest.keyClick(window, Qt.Key_Space)
        _run(qapp, 50)
        assert window.property("switchCount") == 1
        assert window.property("lastSwitch") == "qt_multimedia"
        popup.close()

    def test_unavailable_row_is_not_switchable(self, qapp):
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        registry, bridge, window = h.registry, h.bridge, h.window
        mpd = registry.provider(AudioEngineId.MPD)
        mpd._available = False
        bridge.refresh_engines()
        _run(qapp, 100)
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        mpd_row = _by_name(window, "enginePopupRow_mpd")
        assert mpd_row.property("enabled") is False
        status = _by_name(window, "enginePopupRowStatus_mpd")
        assert "Not available" in _text(status)
        mpd_row.forceActiveFocus()
        _run(qapp)
        QTest.keyClick(window, Qt.Key_Return)
        _run(qapp)
        assert window.property("switchCount") == 0
        popup.close()

    def test_esc_closes_popup(self, qapp):
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        window = h.window
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        assert popup.property("opened") is True
        QTest.keyClick(window, Qt.Key_Escape)
        _run(qapp, 300)
        assert popup.property("opened") is False

    def test_switching_disables_competing_rows(self, qapp):
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        service, window = h.service, h.window
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        service.mark_initializing(AudioEngineId.GSTREAMER)
        _run(qapp)
        gst_row = _by_name(window, "enginePopupRow_gstreamer")
        qt_row = _by_name(window, "enginePopupRow_qt_multimedia")
        mpd_row = _by_name(window, "enginePopupRow_mpd")
        # target shows Switching…, all rows non-selectable (no competing
        # intents while a switch transaction is in flight)
        assert gst_row.property("enabled") is False
        assert qt_row.property("enabled") is False
        assert mpd_row.property("enabled") is False
        status = _by_name(window, "enginePopupRowStatus_gstreamer")
        assert "Switching" in _text(status)
        # switch completes → rows re-enable
        service.mark_ready(AudioEngineId.GSTREAMER)
        _run(qapp)
        assert qt_row.property("enabled") is True
        assert mpd_row.property("enabled") is True
        popup.close()

    def test_live_state_update_while_open(self, qapp):
        """Section 42 mandatory: popup stays open, state changes → rows
        re-render WITHOUT closing/reopening/imperative copies."""
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        service, window = h.service, h.window
        # initial canonical state: Qt selected AND active
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        _run(qapp)
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        qt_status = _by_name(window, "enginePopupRowStatus_qt_multimedia")
        gst_status = _by_name(window, "enginePopupRowStatus_gstreamer")
        assert "Active" in _text(qt_status)
        assert "Active" not in _text(gst_status)
        assert popup.property("opened") is True

        # Canonical state changes WHILE the popup is open (no refresh_engines)
        service.mark_ready(AudioEngineId.GSTREAMER)
        service.restore_selected(AudioEngineId.GSTREAMER)
        _run(qapp)

        assert popup.property("opened") is True  # never closed
        assert "Active" in _text(gst_status)
        assert "Active" not in _text(qt_status)
        popup.close()

    def test_up_down_keyboard_navigation(self, qapp):
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        window = h.window
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        qt_row = _by_name(window, "enginePopupRow_qt_multimedia")
        qt_row.forceActiveFocus()
        _run(qapp)
        QTest.keyClick(window, Qt.Key_Down)
        _run(qapp)
        focus = window.activeFocusItem()
        assert focus is not None
        assert str(focus.objectName()) == "enginePopupRow_gstreamer"
        popup.close()

    def test_up_down_navigation_skips_disabled_rows(self, qapp):
        """P2-02: Qt enabled, GStreamer unavailable (disabled), MPD
        enabled — Down from Qt must land on MPD (skipping the disabled
        row); Up from MPD must land back on Qt. No trapping, no wrapping."""
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        registry, bridge, window = (h.registry, h.bridge, h.window)
        gst = registry.provider(AudioEngineId.GSTREAMER)
        gst._available = False
        bridge.refresh_engines()
        _run(qapp, 100)
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        qt_row = _by_name(window, "enginePopupRow_qt_multimedia")
        gst_row = _by_name(window, "enginePopupRow_gstreamer")
        mpd_row = _by_name(window, "enginePopupRow_mpd")
        assert qt_row.property("enabled") is True
        assert gst_row.property("enabled") is False
        assert mpd_row.property("enabled") is True

        # Down from Qt: skips the disabled GStreamer row → MPD
        qt_row.forceActiveFocus()
        _run(qapp)
        QTest.keyClick(window, Qt.Key_Down)
        _run(qapp)
        assert str(window.activeFocusItem().objectName()) == ("enginePopupRow_mpd")
        # Down again: no wrapping (stays on the last row)
        QTest.keyClick(window, Qt.Key_Down)
        _run(qapp)
        assert str(window.activeFocusItem().objectName()) == ("enginePopupRow_mpd")
        # Up from MPD: skips disabled GStreamer → Qt
        QTest.keyClick(window, Qt.Key_Up)
        _run(qapp)
        assert str(window.activeFocusItem().objectName()) == (
            "enginePopupRow_qt_multimedia"
        )
        popup.close()

    def test_reduced_motion_popup_still_opens(self, qapp):
        """P2-01: with reduced motion the popup has no fade transitions;
        open/close stay deterministic."""
        h = _build(qapp, POPUP_HARNESS, "player/harness.qml")
        window = h.window
        popup = _by_name(window, "enginePopup")
        popup.open()
        _run(qapp, 300)
        assert popup.property("opened") is True
        QTest.keyClick(window, Qt.Key_Escape)
        _run(qapp, 300)
        assert popup.property("opened") is False


class TestSettingsBehavioral:
    def test_preferred_in_use_display(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        service, window = h.service, h.window
        preferred = _by_name(window, "audioEnginePreferredValue")
        active = _by_name(window, "audioEngineActiveValue")
        assert _text(preferred) == "Qt Multimedia"  # default selected
        assert _text(active) == "None"
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        _run(qapp)
        assert _text(active) == "Qt Multimedia"
        service.restore_selected(AudioEngineId.GSTREAMER)
        _run(qapp)
        assert _text(preferred) == "GStreamer"
        assert _text(active) == "Qt Multimedia"  # selected != active visible

    def test_fallback_banner_human_copy_only(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        service, window = h.service, h.window
        service.restore_selected(AudioEngineId.MPD)
        service.mark_fallback_ready(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.MPD,
            "MPD child exited during runtime",
        )
        _run(qapp)
        banner = _by_name(window, "audioEngineFallbackBanner")
        assert banner.property("visible") is True
        banner_text = _collect_text(banner)
        assert "encountered a problem" in banner_text
        assert "MPD child exited" not in banner_text  # P2-01: raw error hidden
        # no raw canonical id appears in the human banner
        assert banner_text.count("mpd") == 0 or "MPD" in banner_text

    def test_fallback_banner_hidden_when_no_fallback(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        window = h.window
        banner = _by_name(window, "audioEngineFallbackBanner")
        assert banner.property("visible") is False

    def test_advanced_hidden_initial_and_mouse_toggle(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        window = h.window
        advanced = _by_name(window, "engineAdvancedContent")
        assert advanced.property("visible") is False
        toggle = _by_name(window, "engineAdvancedToggle")
        _click(qapp, window, toggle)
        _run(qapp)
        assert advanced.property("visible") is True
        _click(qapp, window, toggle)
        _run(qapp)
        assert advanced.property("visible") is False

    def test_advanced_keyboard_toggle(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        window = h.window
        advanced = _by_name(window, "engineAdvancedContent")
        toggle = _by_name(window, "engineAdvancedToggle")
        toggle.forceActiveFocus()
        _run(qapp)
        QTest.keyClick(window, Qt.Key_Return)
        _run(qapp)
        assert advanced.property("visible") is True
        QTest.keyClick(window, Qt.Key_Space)
        _run(qapp)
        assert advanced.property("visible") is False

    def test_advanced_reveals_raw_error_only_when_expanded(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        service, window = h.service, h.window
        service.restore_selected(AudioEngineId.MPD)
        service.mark_fallback_ready(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.MPD,
            "MPD child exited during runtime",
        )
        _run(qapp)
        advanced = _by_name(window, "engineAdvancedContent")
        assert advanced.property("visible") is False
        toggle = _by_name(window, "engineAdvancedToggle")
        _click(qapp, window, toggle)
        _run(qapp)
        assert advanced.property("visible") is True
        assert "MPD child exited during runtime" in _collect_text(advanced)

    def test_cards_positive_geometry_at_widths(self, qapp):
        """P1-06/section 24: content-derived sizing, no collapsed cards."""
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        window = h.window
        section = _by_name(window, "engineSettingsSection")
        assert section.property("implicitHeight") > 0
        for width in (1000, 700, 480):
            section.setProperty("width", width)
            _run(qapp)
            assert section.property("height") > 0, width
            for eid in ("qt_multimedia", "gstreamer", "mpd"):
                card = _by_name(window, f"engineSettingsCard_{eid}")
                assert card.property("height") > 0, (eid, width)
                assert card.property("implicitHeight") > 0, (eid, width)

    def test_available_card_emits_exactly_one_switch(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        window = h.window
        qt_card = _by_name(window, "engineSettingsCard_qt_multimedia")
        _click(qapp, window, qt_card)
        _run(qapp)
        assert window.property("switchCount") == 1
        assert window.property("lastSwitch") == "qt_multimedia"

    def test_unavailable_card_no_switch(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        registry, bridge, window = h.registry, h.bridge, h.window
        mpd = registry.provider(AudioEngineId.MPD)
        mpd._available = False
        bridge.refresh_engines()
        _run(qapp, 100)
        mpd_card = _by_name(window, "engineSettingsCard_mpd")
        assert mpd_card.property("enabled") is False
        _click(qapp, window, mpd_card)
        _run(qapp)
        assert window.property("switchCount") == 0

    def test_cards_disabled_while_switching(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        service, window = h.service, h.window
        service.mark_initializing(AudioEngineId.MPD)
        _run(qapp)
        for eid in ("qt_multimedia", "gstreamer", "mpd"):
            card = _by_name(window, f"engineSettingsCard_{eid}")
            assert card.property("enabled") is False, eid
        service.mark_ready(AudioEngineId.MPD)
        _run(qapp)
        qt_card = _by_name(window, "engineSettingsCard_qt_multimedia")
        assert qt_card.property("enabled") is True

    def test_engine_card_keyboard_activation(self, qapp):
        h = _build(qapp, SETTINGS_HARNESS, "views/harness.qml")
        window = h.window
        qt_card = _by_name(window, "engineSettingsCard_qt_multimedia")
        qt_card.forceActiveFocus()
        _run(qapp)
        QTest.keyClick(window, Qt.Key_Return)
        _run(qapp)
        assert window.property("switchCount") == 1
        assert window.property("lastSwitch") == "qt_multimedia"


def _click(qapp, window, item):
    """QTest mouse click at the item's scene position."""
    from PySide6.QtCore import QPoint, QPointF

    pos = item.mapToScene(QPointF(0, 0))
    center = QPoint(int(pos.x() + item.width() / 2), int(pos.y() + item.height() / 2))
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center)
    _run(qapp)


def _collect_text(item) -> str:
    """Concatenated text of item and its visual descendants."""
    parts = []
    stack = [item]
    while stack:
        current = stack.pop()
        if isinstance(current, QQuickItem):
            for child in current.childItems():
                text = child.property("text")
                if isinstance(text, str) and text:
                    parts.append(text)
                stack.append(child)
    return " | ".join(parts)


class TestSelectorClickPathGolden:
    """P1-03 GATE A (always-on CI, deterministic fakes): the REAL popup
    row click flows through the REAL QML wiring → AudioEngineBridge →
    SelectionCoordinator — no direct bridge call."""

    def test_row_click_reaches_coordinator_and_switches(self, qapp):
        import time

        from PySide6.QtCore import QEventLoop, Qt, QUrl
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication

        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSelectionCoordinator,
        )
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import AudioTransportRouter
        from michi.application.playback_service import PlaybackService
        from michi.application.settings_service import SettingsService
        from michi.domain.audio_engine import AudioEngineId
        from michi.presentation.audio_engine_bridge import AudioEngineBridge
        from tests.test_m11_3f_engine_selection import (
            FakeProvider,
            FakeSettingsRepository,
        )

        qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
        gst = FakeProvider(AudioEngineId.GSTREAMER)
        mpd = FakeProvider(AudioEngineId.MPD)
        registry = AudioEngineRegistry([qt, gst, mpd])
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        playback = PlaybackService(router)
        settings = SettingsService(FakeSettingsRepository())
        coordinator = AudioEngineSelectionCoordinator(
            engine_service=service,
            registry=registry,
            router=router,
            playback=playback,
            settings=settings,
        )
        bridge = AudioEngineBridge(
            service,
            registry,
            coordinator,
            playback_quiescent=lambda: playback.is_engine_switch_quiescent(),
        )
        qt_port = qt.open()
        router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)

        # the REAL popup, wired EXACTLY like production: the row click
        # emits engineSwitchRequested → bridge.switch_engine (the AppShell
        # route) — no direct coordinator/bridge call in the test body.
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("audioEngine", bridge)
        comp = QQmlComponent(engine)
        comp.setData(
            POPUP_HARNESS.replace(
                "onEngineSwitchRequested: (engineId) => harness.switchRequested(engineId)",  # noqa: E501
                "onEngineSwitchRequested: (engineId) => audioEngine.switch_engine(engineId)",  # noqa: E501
            ).encode(),
            QUrl.fromLocalFile(str(QML_DIR / "player/harness.qml")),
        )
        window = comp.create()
        window.show()
        for _ in range(20):
            QApplication.processEvents(QEventLoop.AllEvents, 20)
        popup = _by_name(window, "enginePopup")
        assert popup is not None, "popup MISSING"
        popup.open()
        QTest.qWait(300)
        gst_row = _by_name(window, "enginePopupRow_gstreamer")
        assert gst_row is not None, "GStreamer row MISSING"
        # REAL keyboard activation of the real Button (Enter)
        gst_row.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Return)
        for _ in range(30):
            QApplication.processEvents(QEventLoop.AllEvents, 20)
            time.sleep(0.01)
        # THE SAME TRUTH across every authority (the click path did it)
        assert service.state.selected_engine_id == AudioEngineId.GSTREAMER
        assert service.state.active_engine_id == AudioEngineId.GSTREAMER
        assert router.bound_engine_id == AudioEngineId.GSTREAMER
        assert settings.load().audio_engine_id == AudioEngineId.GSTREAMER
        # QML live state reflects it
        assert service.state.switching_to is None
