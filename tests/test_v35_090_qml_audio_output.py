"""DAC-V35-090 UI90-22..47 — real QML audio-output presentation gates."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from michi.application.audio_device_registry import AudioDeviceTopologyChange
from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from michi.domain.audio_evidence import CapabilityEvidence, EvidenceStrength, PcmTuple
from michi.presentation.audio_output_bridge import AudioOutputBridge

QML_DIR = Path("src/michi/presentation/qml").resolve()

PY_SHARED_ROW = {
    "stableDeviceId": "",
    "displayName": "System Output",
    "available": True,
    "selected": False,
    "active": True,
    "connectionLabel": "Available",
    "statusLabel": "In use",
    "transportMode": "shared",
    "transportLabel": "Shared",
    "volumeLabel": "Software volume",
    "signalTruthLabel": "Not verified",
    "sourceRateLabel": "—",
    "deviceRateLabel": "—",
    "canSelect": True,
    "isShared": True,
}
PY_DEVICE_ROW = {
    "stableDeviceId": "usb:1:2:serial-abc",
    "shortenedStableDeviceId": "usb:1:2:…ial-abc",
    "displayName": "Example Reference DAC",
    "available": True,
    "selected": True,
    "active": False,
    "connectionLabel": "Available",
    "statusLabel": "Selected · inactive",
    "identityConfidence": "strong",
    "alsaLocator": "hw:CARD=DAC,DEV=0",
    "vendorId": "1234",
    "productId": "5678",
    "bcdDevice": "0100",
    "generation": 2,
    "transportMode": "direct",
    "transportLabel": "Direct",
    "volumeLabel": "Fixed output · unity gain",
    "signalTruthLabel": "Not verified",
    "sourceRateLabel": "44.1 kHz",
    "deviceRateLabel": "44.1 kHz",
    "capabilityEvidenceLabel": "Unknown",
    "environmentFingerprint": "kernel=test;alsa=test",
    "runtimeSinkSummary": "playbin3 → audioconvert → alsasink",
    "lastFailureCode": "",
    "canSelect": True,
    "isShared": False,
}
PY_PATH_ROWS = [
    {"title": stage, "summary": "S24_LE · 44.1 kHz"}
    for stage in ("Source", "Decoded", "Engine", "Device")
]
PY_PROFILE_ROWS = [
    {
        "profileId": "direct:reference",
        "stableDeviceId": "usb:1:2:serial-abc",
        "displayName": "Example Reference DAC — Direct",
        "deviceName": "Example Reference DAC",
        "pathLabel": "Direct",
        "available": True,
        "selected": True,
        "actionEnabled": True,
        "statusLabel": "Selected · available",
    }
]

DEVICE_ROW = """
({
    stableDeviceId: "usb:1:2:serial-abc",
    shortenedStableDeviceId: "usb:1:2:…ial-abc",
    displayName: "Example Reference DAC",
    manufacturer: "Example",
    product: "Reference DAC",
    available: true,
    selected: true,
    active: false,
    reconnecting: false,
    connectionLabel: "Available",
    statusLabel: "Selected · inactive",
    identityConfidence: "strong",
    alsaLocator: "hw:CARD=DAC,DEV=0",
    vendorId: "1234",
    productId: "5678",
    bcdDevice: "0100",
    generation: 2,
    profileId: "stable_direct_preset",
    profileName: "Direct",
    transportMode: "direct",
    transportLabel: "Direct",
    volumeLabel: "Fixed output · unity gain",
    signalTruthLabel: "Not verified",
    sourceRateLabel: "44.1 kHz",
    deviceRateLabel: "44.1 kHz",
    capabilityEvidenceLabel: "Unknown",
    environmentFingerprint: "kernel=test;alsa=test",
    runtimeSinkSummary: "playbin3 → audioconvert → alsasink",
    lastFailureCode: "",
    canSelect: true,
    isShared: false
})
"""

SHARED_ROW = """
({
    stableDeviceId: "",
    displayName: "System Output",
    available: true,
    selected: false,
    active: true,
    connectionLabel: "Available",
    statusLabel: "In use",
    transportMode: "shared",
    transportLabel: "Shared",
    volumeLabel: "Software volume",
    signalTruthLabel: "Not verified",
    sourceRateLabel: "—",
    deviceRateLabel: "—",
    canSelect: true,
    isShared: true
})
"""

SETTINGS_HARNESS = f"""
import QtQuick
import QtQuick.Controls.Basic
import "../views"

Window {{
    id: harness
    visible: true
    width: 1000
    height: 800
    color: "#000000"
    property int deviceRequests: 0
    property int sharedRequests: 0
    property int profileRequests: 0
    property string requestedProfileId: ""
    property var rows: [{SHARED_ROW}, {DEVICE_ROW}]
    property var pathRows: [
        ({{title: "Source", summary: "FLAC · 44.1 kHz"}}),
        ({{title: "Decoded", summary: "S24_LE · 44.1 kHz"}}),
        ({{title: "Engine", summary: "S24_LE · 44.1 kHz"}}),
        ({{title: "Device", summary: "S24_LE · 44.1 kHz"}})
    ]

    AudioOutputSettingsSection {{
        objectName: "outputSettings"
        anchors.left: parent.left
        anchors.top: parent.top
        x: 32
        width: parent.width - 64
        devices: harness.rows
        profiles: [{{
            "profileId": "direct:reference",
            "displayName": "Example Reference DAC — Direct",
            "available": true,
            "selected": true,
            "actionEnabled": true
        }}]
        selectedProfileId: "direct:reference"
        signalPath: harness.pathRows
        signalTruthReasonCodes: ["RUNTIME_EVIDENCE_INCOMPLETE"]
        canUseDirect: true
        onDeviceSelectionRequested: harness.deviceRequests++
        onSharedSelectionRequested: harness.sharedRequests++
        onProfileSelectionRequested: profileId => {{
            harness.profileRequests++
            harness.requestedProfileId = profileId
        }}
    }}
}}
"""

POPUP_HARNESS = f"""
import QtQuick
import QtQuick.Controls.Basic
import "../player"

Window {{
    id: harness
    visible: true
    width: 700
    height: 600
    color: "#000000"
    property int deviceRequests: 0
    property int sharedRequests: 0
    property int settingsRequests: 0
    property var rows: [{SHARED_ROW}, {DEVICE_ROW}]

    Item {{
        anchors.fill: parent
        Button {{
            id: opener
            objectName: "outputPopupOpener"
            text: "Output"
        }}
        AudioOutputPopup {{
            id: popup
            objectName: "outputPopup"
            x: 40
            y: 40
            devices: harness.rows
            focusReturnTarget: opener
            onDeviceSelectionRequested: harness.deviceRequests++
            onSharedSelectionRequested: harness.sharedRequests++
            onSettingsRequested: harness.settingsRequests++
        }}
    }}
    Component.onCompleted: {{
        opener.forceActiveFocus()
        popup.open()
    }}
}}
"""

NOW_PLAYING_HARNESS = """
import QtQuick
import QtQuick.Controls.Basic
import "../player"

Window {
    id: harness
    visible: true
    width: 1280
    height: 500
    color: "#000000"

    NowPlayingBar {
        id: bar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: implicitHeight
        currentPath: "/music/example.flac"
        trackTitle: "Example Track"
        artist: "Example Artist"
        canSelectOutput: true
        outputDevices: []
    }
}
"""

PRODUCTIVE_POPUP_HARNESS = """
import QtQuick
import QtQuick.Controls.Basic
import "../player"

Window {
    id: harness
    visible: true
    width: 1280
    height: 500
    color: "#000000"
    property int deviceRequests: 0
    property int sharedRequests: 0

    NowPlayingBar {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: implicitHeight
        canSelectOutput: true
        outputDevices: audioOutput.devices
        outputTooltip: audioOutput.outputTooltip
        outputSignalTruthLabel: audioOutput.signalTruthLabel
        outputFailureTitle: audioOutput.lastFailureTitle
        onAudioOutputDeviceSelectionRequested: stableDeviceId => {
            harness.deviceRequests++
        }
        onAudioOutputSharedSelectionRequested: harness.sharedRequests++
    }
}
"""


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _create(qapp, code: str, base_rel: str):
    engine = QQmlEngine()
    qml_warnings = []
    engine.warnings.connect(
        lambda items: qml_warnings.extend(str(item) for item in items)
    )
    engine._michi_test_warnings = qml_warnings
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.setData(code.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / base_rel)))
    assert component.status() == QQmlComponent.Ready, component.errorString()
    window = component.create()
    assert window is not None, component.errorString()
    section = window.findChild(QObject, "outputSettings")
    if section is not None:
        section.setProperty("devices", [PY_SHARED_ROW, PY_DEVICE_ROW])
        section.setProperty("profiles", PY_PROFILE_ROWS)
        section.setProperty("selectedProfileId", "direct:reference")
        section.setProperty("signalPath", PY_PATH_ROWS)
    popup = window.findChild(QObject, "outputPopup")
    if popup is not None:
        popup.setProperty("devices", [PY_SHARED_ROW, PY_DEVICE_ROW])
    window.show()
    for _ in range(10):
        QApplication.processEvents()
    return engine, component, window


def _create_productive_popup(qapp, tmp_path: Path):
    from tests.dac.test_v35_productive_direct_composition import (
        _accept_current,
        _direct_graph,
    )

    graph, bindings = _direct_graph(tmp_path)
    graph.playback.load_and_play(tmp_path / "active.flac")
    _accept_current(graph, bindings)
    coordinator = AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )
    bridge = AudioOutputBridge(
        graph.volume_policy,
        graph.playback,
        graph.signal_truth,
        devices=graph.audio_device_registry,
        profiles=graph.audio_output_profiles,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
        selection_coordinator=coordinator,
    )
    engine = QQmlEngine()
    qml_warnings = []
    engine.warnings.connect(
        lambda items: qml_warnings.extend(str(item) for item in items)
    )
    engine._michi_test_warnings = qml_warnings
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("audioOutput", bridge)
    component = QQmlComponent(engine)
    component.setData(
        PRODUCTIVE_POPUP_HARNESS.encode("utf-8"),
        QUrl.fromLocalFile(str(QML_DIR / "tests/ui90r11-productive-popup.qml")),
    )
    assert component.status() == QQmlComponent.Ready, component.errorString()
    window = component.create()
    assert window is not None, component.errorString()
    window.show()
    for _ in range(10):
        QApplication.processEvents()
    popup = window.findChild(QObject, "AudioOutputPopup")
    assert popup is not None
    assert QMetaObject.invokeMethod(popup, "open")
    QTest.qWait(300)
    QApplication.processEvents()
    return SimpleNamespace(
        graph=graph,
        bindings=bindings,
        bridge=bridge,
        engine=engine,
        component=component,
        window=window,
        popup=popup,
    )


def _productive_disconnect(harness, tmp_path: Path) -> None:
    from tests.dac._fixtures import remove_alsa_card, remove_usb_device

    sysfs = tmp_path / "linux-topology" / "sys"
    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)
    harness.graph.udev_observer.handle_event(
        action="remove", subsystem="sound", sys_name="card1"
    )
    QApplication.processEvents()


def _productive_reconnect(harness, tmp_path: Path) -> None:
    from tests.dac._fixtures import AlsaCard, UsbDevice, build_linux_sysfs

    sysfs = tmp_path / "linux-topology" / "sys"
    build_linux_sysfs(
        sysfs,
        usb_devices=(
            UsbDevice("2-1", "2622", "0105", serial="DX5ABC123", bcd_device="0100"),
        ),
        cards=(AlsaCard(4, "DX5", "2-1"),),
    )
    harness.graph.udev_observer.handle_event(
        action="add", subsystem="sound", sys_name="card4"
    )
    QApplication.processEvents()


def _close_productive_popup(harness) -> None:
    from tests.dac.test_v35_productive_direct_composition import _close_graph

    harness.window.close()
    harness.bridge.dispose()
    harness.graph.direct_output_lifecycle.shutdown()
    _close_graph(harness.graph)


def _source(relative: str) -> str:
    return (QML_DIR / relative).read_text(encoding="utf-8")


def _visual_item(window, object_name: str):
    roots = [window.contentItem()] if isinstance(window, QQuickWindow) else []
    roots.extend(
        item
        for item in window.findChildren(QQuickItem)
        if item.parent() is window and item not in roots
    )
    pending = list(roots)
    while pending:
        item = pending.pop()
        if item.objectName() == object_name:
            return item
        pending.extend(item.childItems())
    return None


def _open_popup(window):
    popup = window.findChild(QObject, "outputPopup")
    assert popup is not None
    assert QMetaObject.invokeMethod(popup, "open")
    QTest.qWait(300)
    QApplication.processEvents()
    return popup


def _click(window, item) -> None:
    origin = item.mapToScene(QPointF(0, 0))
    center = QPoint(
        int(origin.x() + item.width() / 2),
        int(origin.y() + item.height() / 2),
    )
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center)
    QApplication.processEvents()


def _accessible_name(item) -> str:
    from PySide6.QtGui import QAccessible

    interface = QAccessible.queryAccessibleInterface(item)
    assert interface is not None
    return interface.text(QAccessible.Text.Name)


def test_ui90_22_settings_section_instantiates_with_positive_geometry(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    assert section is not None
    assert section.property("height") > 0
    assert _visual_item(window, "audioOutputDeviceCard_shared") is not None
    window.close()


def test_ui90_23_normal_card_shows_required_truthful_summary() -> None:
    source = _source("components/DacDeviceCard.qml")
    for projection in (
        "displayName",
        "connectionLabel",
        "statusLabel",
        "transportLabel",
        "sourceRateLabel",
        "deviceRateLabel",
        "volumeLabel",
        "signalTruthLabel",
    ):
        assert projection in source


def test_ui90_24_raw_identifiers_are_confined_to_advanced_diagnostics() -> None:
    card = _source("components/DacDeviceCard.qml")
    diagnostics = _source("components/DacDiagnosticsDisclosure.qml")
    for raw in ("alsaLocator", "vendorId", "productId", "bcdDevice"):
        assert raw not in card
        assert raw in diagnostics


def test_ui90_25_advanced_content_starts_collapsed(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    content = _visual_item(window, "dacAdvancedContent_usb:1:2:serial-abc")
    assert content is not None
    assert content.property("visible") is False
    window.close()


def test_ui90_26_advanced_disclosure_expands_without_changing_authority(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    toggle = _visual_item(window, "dacAdvancedToggle_usb:1:2:serial-abc")
    content = _visual_item(window, "dacAdvancedContent_usb:1:2:serial-abc")
    assert toggle is not None and content is not None
    _click(window, toggle)
    assert content.property("visible") is True
    assert window.property("deviceRequests") == 0
    window.close()


def test_ui90_27_signal_truth_panel_has_four_runtime_stages() -> None:
    source = _source("components/SignalTruthPanel.qml")
    assert "model: root.stages" in source
    assert "modelData.title" in source
    assert "modelData.summary" in source


def test_ui90_28_diagnostics_expose_bounded_evidence_fields() -> None:
    source = _source("components/DacDiagnosticsDisclosure.qml")
    for field in (
        "shortenedStableDeviceId",
        "identityConfidence",
        "environmentFingerprint",
        "capabilityEvidenceLabel",
        "runtimeSinkSummary",
        "lastFailureCode",
    ):
        assert field in source


def test_ui90_29_normal_surface_contains_no_forbidden_claims() -> None:
    sources = "\n".join(
        _source(path)
        for path in (
            "components/DacDeviceCard.qml",
            "views/AudioOutputSettingsSection.qml",
            "player/AudioOutputPopup.qml",
        )
    ).casefold()
    for claim in ("verified bit-perfect", "michi verified", "exclusive verified"):
        assert claim not in sources


def test_ui90_30_dac_volume_control_remains_the_only_volume_surface() -> None:
    section = _source("views/AudioOutputSettingsSection.qml")
    card = _source("components/DacDeviceCard.qml")
    assert "Slider" not in section + card
    assert "set_volume" not in section + card
    assert _source("player/NowPlayingBar.qml").count("DacVolumeControl {") == 1


def test_ui90_31_settings_refresh_is_event_driven_without_polling() -> None:
    source = _source("views/SettingsView.qml")
    assert "audioOutput.refresh_devices()" in source
    assert "Timer" not in source


def test_ui90_32_output_button_uses_bridge_capability_and_tooltip() -> None:
    source = _source("player/NowPlayingBar.qml")
    assert "enabled: root.canSelectOutput" in source
    assert "accessibleName: root.outputTooltip" in source


def test_ui90_33_output_popup_instantiates_open_with_two_rows(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    popup = _open_popup(window)
    assert popup.property("opened") is True
    assert _visual_item(window, "outputPopupRow_shared") is not None
    assert _visual_item(window, "outputPopupRow_usb:1:2:serial-abc") is not None
    window.close()


def test_ui90_34_popup_shared_row_emits_explicit_shared_intent(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    _open_popup(window)
    row = _visual_item(window, "outputPopupRow_shared")
    assert row is not None
    _click(window, row)
    assert window.property("sharedRequests") == 1
    assert window.property("deviceRequests") == 0
    window.close()


def test_ui90_35_popup_physical_row_emits_stable_identity(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    _open_popup(window)
    row = _visual_item(window, "outputPopupRow_usb:1:2:serial-abc")
    assert row is not None
    _click(window, row)
    assert window.property("deviceRequests") == 1
    assert window.property("sharedRequests") == 0
    window.close()


def test_ui90_36_popup_focuses_first_enabled_row(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    _open_popup(window)
    row = _visual_item(window, "outputPopupRow_shared")
    assert row is not None
    assert row.property("activeFocus") is True
    window.close()


def test_ui90_37_popup_declares_arrow_keyboard_navigation() -> None:
    source = _source("player/AudioOutputPopup.qml")
    assert "KeyNavigation.up" in source
    assert "KeyNavigation.down" in source
    assert "while (i >= 0 && i < outputRows.count)" in source


def test_ui90_38_popup_declares_enter_activation() -> None:
    source = _source("player/AudioOutputPopup.qml")
    assert "Keys.onReturnPressed: row.clicked()" in source
    assert "Keys.onEnterPressed: row.clicked()" in source


def test_ui90_39_popup_escape_close_policy_is_explicit() -> None:
    source = _source("player/AudioOutputPopup.qml")
    assert "Popup.CloseOnEscape" in source


def test_ui90_40_popup_restores_focus_to_output_button() -> None:
    source = _source("player/AudioOutputPopup.qml")
    assert "root.focusReturnTarget.forceActiveFocus()" in source


def test_ui90_41_popup_exposes_settings_navigation(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    _open_popup(window)
    button = _visual_item(window, "openAudioOutputSettingsButton")
    assert button is not None
    _click(window, button)
    assert window.property("settingsRequests") == 1
    window.close()


def test_ui90_42_player_refreshes_output_only_when_popup_opens() -> None:
    source = _source("player/NowPlayingBar.qml")
    assert "outputPopup.open()" in source
    assert "root.audioOutputRefreshRequested()" in source
    assert "Timer" not in source


def test_ui90_43_popup_rows_remain_live_bound_to_device_projection() -> None:
    source = _source("player/NowPlayingBar.qml")
    assert "devices: root.outputDevices" in source
    assert "outputPopup.devices =" not in source


def test_ui90_44_typed_action_failures_reach_existing_toast() -> None:
    source = _source("shell/AppShell.qml")
    assert "function onAction_failed(code, title, explanation)" in source
    assert 'root.showToast(title + ": " + explanation, "error")' in source


def test_ui90_45_settings_cards_use_responsive_single_column_layout() -> None:
    source = _source("views/AudioOutputSettingsSection.qml")
    assert 'objectName: "audioOutputDeviceCards"' in source
    assert "ColumnLayout" in source
    assert "Layout.fillWidth: true" in source


def test_ui90_46_now_playing_geometry_and_playback_zone_are_unchanged() -> None:
    source = _source("player/NowPlayingBar.qml")
    assert "implicitHeight: 154" in source
    assert 'objectName: "playbackZone"' in source
    assert source.count('objectName: "outputDeviceButton"') == 1


def test_ui90_47_new_surfaces_define_accessible_names_and_reduced_motion() -> None:
    sources = "\n".join(
        _source(path)
        for path in (
            "components/DacDeviceCard.qml",
            "components/DacDiagnosticsDisclosure.qml",
            "player/AudioOutputPopup.qml",
        )
    )
    assert sources.count("Accessible.name") >= 3
    assert "MichiAccessibility.reducedMotion" in sources


def test_ui90r1_06_settings_instantiates_real_output_profile_selector(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    selector = _visual_item(window, "audioOutputProfileSelector")
    assert selector is not None
    assert selector.property("currentText") == "Example Reference DAC — Direct"
    assert selector.property("accessibleName") == "Output profile"
    window.close()


def test_ui90r1_07_profile_selector_is_wired_to_bridge_intent() -> None:
    section = _source("views/AudioOutputSettingsSection.qml")
    settings = _source("views/SettingsView.qml")
    assert "profileSelectionRequested(profile.profileId)" in section
    assert "audioOutput.select_profile(profileId)" in settings
    assert "audioEngine" not in section


def test_pc13_03_ui_path_mode_control_is_wired_to_bridge_intent() -> None:
    """R1.3: the UI expresses device identity AND transport policy."""
    section = _source("views/AudioOutputSettingsSection.qml")
    settings = _source("views/SettingsView.qml")
    assert "audioOutputPathModeSelector" in section
    assert "pathModeSelectionRequested(entry.mode)" in section
    assert "onPathModeSelectionRequested" in settings
    assert "audioOutput.select_path_mode(mode)" in settings
    assert "audioOutput.selectedPathMode" in settings


def test_ui90r1_08_escape_really_closes_popup_and_restores_focus(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    popup = _open_popup(window)
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(250)
    QApplication.processEvents()
    opener = _visual_item(window, "outputPopupOpener")
    assert popup.property("opened") is False
    assert opener is not None and opener.property("activeFocus") is True
    window.close()


def test_ui90r1_09_open_really_focuses_first_enabled_row(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    _open_popup(window)
    shared = _visual_item(window, "outputPopupRow_shared")
    assert shared is not None and shared.property("activeFocus") is True
    window.close()


def test_ui90r1_10_down_arrow_really_moves_focus(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    _open_popup(window)
    QTest.keyClick(window, Qt.Key_Down)
    QApplication.processEvents()
    device = _visual_item(window, "outputPopupRow_usb:1:2:serial-abc")
    assert device is not None and device.property("activeFocus") is True
    window.close()


def test_ui90r1_11_arrows_really_skip_disabled_rows(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    popup = _open_popup(window)
    unavailable = dict(PY_DEVICE_ROW)
    unavailable.update(
        stableDeviceId="usb:disabled",
        displayName="Unavailable DAC",
        available=False,
        canSelect=False,
        selected=False,
    )
    available = dict(PY_DEVICE_ROW)
    available.update(
        stableDeviceId="usb:available", displayName="Available DAC", selected=False
    )
    popup.setProperty("devices", [PY_SHARED_ROW, unavailable, available])
    QApplication.processEvents()
    shared = _visual_item(window, "outputPopupRow_shared")
    shared.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Down)
    QApplication.processEvents()
    target = _visual_item(window, "outputPopupRow_usb:available")
    disabled = _visual_item(window, "outputPopupRow_usb:disabled")
    assert target is not None and target.property("activeFocus") is True
    assert disabled is not None and disabled.property("activeFocus") is False
    window.close()


def test_ui90r1_12_enter_really_activates_focused_row(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    _open_popup(window)
    QTest.keyClick(window, Qt.Key_Return)
    QApplication.processEvents()
    assert window.property("sharedRequests") == 1
    assert window.property("deviceRequests") == 0
    window.close()


def test_ui90r1_13_popup_live_adds_device_while_open(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    popup = _open_popup(window)
    added = dict(PY_DEVICE_ROW)
    added.update(
        stableDeviceId="usb:hotplug", displayName="Hotplug DAC", selected=False
    )
    popup.setProperty("devices", [PY_SHARED_ROW, PY_DEVICE_ROW, added])
    QApplication.processEvents()
    assert popup.property("opened") is True
    assert _visual_item(window, "outputPopupRow_usb:hotplug") is not None
    window.close()


def test_ui90r1_14_popup_disconnect_disables_without_auto_selection(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    popup = _open_popup(window)
    disconnected = dict(PY_DEVICE_ROW)
    disconnected.update(
        available=False, canSelect=False, statusLabel="Selected · unavailable"
    )
    popup.setProperty("devices", [PY_SHARED_ROW, disconnected])
    QApplication.processEvents()
    row = _visual_item(window, "outputPopupRow_usb:1:2:serial-abc")
    assert popup.property("opened") is True
    assert row is not None and row.property("enabled") is False
    assert window.property("deviceRequests") == 0
    assert window.property("sharedRequests") == 0
    window.close()


def test_ui90r1_15_popup_reconnect_enables_without_claiming_active(qapp) -> None:
    _engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    popup = _open_popup(window)
    disconnected = dict(PY_DEVICE_ROW)
    disconnected.update(available=False, canSelect=False, active=False)
    popup.setProperty("devices", [PY_SHARED_ROW, disconnected])
    QApplication.processEvents()
    reconnected = dict(disconnected)
    reconnected.update(
        available=True, canSelect=True, statusLabel="Selected · inactive"
    )
    popup.setProperty("devices", [PY_SHARED_ROW, reconnected])
    QApplication.processEvents()
    row = _visual_item(window, "outputPopupRow_usb:1:2:serial-abc")
    assert row is not None and row.property("enabled") is True
    assert reconnected["active"] is False
    assert window.property("deviceRequests") == 0
    window.close()


def test_ui90r11_05_12_productive_open_popup_hotplug_reconnect_and_stale_firewall(
    qapp, tmp_path: Path
) -> None:
    """UI90R1.1-05..12: registry -> bridge -> NowPlayingBar -> open popup."""
    harness = _create_productive_popup(qapp, tmp_path)
    try:
        graph = harness.graph
        stable_id = graph.output_session.active_device_id
        assert stable_id is not None
        old_generation = graph.audio_device_registry.generation_for(stable_id)
        old_bindings = graph.audio_device_registry.bindings_for(stable_id)
        engine_before = graph.audio_engine_service.state.active_engine_id
        row_name = f"outputPopupRow_{stable_id}"

        assert "outputDevices: audioOutput.devices" in PRODUCTIVE_POPUP_HARNESS
        assert "popup.setProperty" not in PRODUCTIVE_POPUP_HARNESS
        assert harness.popup.property("opened") is True
        row = _visual_item(harness.window, row_name)
        assert row is not None
        assert "Selected · Active" in _accessible_name(row)

        _productive_disconnect(harness, tmp_path)

        row = _visual_item(harness.window, row_name)
        projected = next(
            item
            for item in harness.bridge.devices
            if item["stableDeviceId"] == stable_id
        )
        assert harness.popup.property("opened") is True
        assert row is not None and row.property("enabled") is False
        assert "Selected · unavailable" in _accessible_name(row)
        assert projected["selected"] is True
        assert projected["available"] is False
        assert projected["active"] is False
        assert harness.window.property("deviceRequests") == 0
        assert harness.window.property("sharedRequests") == 0

        _productive_reconnect(harness, tmp_path)

        row = _visual_item(harness.window, row_name)
        projected = next(
            item
            for item in harness.bridge.devices
            if item["stableDeviceId"] == stable_id
        )
        new_generation = graph.audio_device_registry.generation_for(stable_id)
        assert harness.popup.property("opened") is True
        assert row is not None and row.property("enabled") is True
        assert "Selected · inactive" in _accessible_name(row)
        assert projected["available"] is True
        assert projected["selected"] is True
        assert projected["active"] is False
        assert new_generation is not None and new_generation > old_generation
        assert harness.window.property("deviceRequests") == 0
        assert harness.window.property("sharedRequests") == 0

        graph.dac_qualification.cache_evidence(
            stable_id,
            (
                CapabilityEvidence(
                    stable_device_id=stable_id,
                    tuple=PcmTuple(96_000, "S32_LE", 2, 24),
                    supported=True,
                    strength=EvidenceStrength.OPENED,
                    source="michi-alsa-probe",
                    observed_at_ns=time.time_ns(),
                    environment_fingerprint=(
                        graph.dac_qualification.current_environment_fingerprint(
                            stable_id
                        )
                    ),
                    evidence_refs=("probe:ui90r11-g2",),
                ),
            ),
        )
        graph.playback.play()
        from tests.dac.test_v35_productive_direct_composition import _accept_current

        _accept_current(graph, harness.bindings)
        QApplication.processEvents()

        row = _visual_item(harness.window, row_name)
        assert harness.popup.property("opened") is True
        assert row is not None
        assert "Selected · Active" in _accessible_name(row)
        projected = next(
            item
            for item in harness.bridge.devices
            if item["stableDeviceId"] == stable_id
        )
        assert projected["generation"] == new_generation

        graph.direct_output_lifecycle.handle_topology_changed(
            AudioDeviceTopologyChange(
                stable_device_id=stable_id,
                previous_available=True,
                current_available=False,
                previous_generation=old_generation,
                current_generation=new_generation - 1,
                previous_bindings=old_bindings,
                current_bindings=(),
            )
        )
        QApplication.processEvents()

        row = _visual_item(harness.window, row_name)
        assert harness.popup.property("opened") is True
        assert row is not None
        assert "Selected · Active" in _accessible_name(row)
        projected = next(
            item
            for item in harness.bridge.devices
            if item["stableDeviceId"] == stable_id
        )
        assert projected["generation"] == new_generation
        assert graph.output_session.active_device_id == stable_id
        assert graph.audio_engine_service.state.active_engine_id is engine_before
        assert harness.window.property("deviceRequests") == 0
        assert harness.window.property("sharedRequests") == 0
        assert harness.engine._michi_test_warnings == []
    finally:
        _close_productive_popup(harness)


def test_ui90r1_21_empty_profile_model_disables_selector(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    section.setProperty("profiles", [])
    section.setProperty("selectedProfileId", "")
    QApplication.processEvents()
    selector = _visual_item(window, "audioOutputProfileSelector")
    assert selector is not None and selector.property("enabled") is False
    assert selector.property("count") == 0
    window.close()


def test_ui90r1_19_shared_selection_does_not_display_first_direct_profile(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    section.setProperty("selectedProfileId", "")
    QApplication.processEvents()
    selector = _visual_item(window, "audioOutputProfileSelector")
    assert selector is not None
    assert selector.property("currentIndex") == -1
    assert selector.property("currentText") == ""
    window.close()


def test_ui90r1_22_single_profile_is_selected_from_authority(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    selector = _visual_item(window, "audioOutputProfileSelector")
    assert selector.property("count") == 1
    assert selector.property("currentIndex") == 0
    assert selector.property("currentText") == "Example Reference DAC — Direct"
    window.close()


def test_ui90r1_23_mouse_click_really_emits_exact_profile_id(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    second = dict(PY_PROFILE_ROWS[0])
    second.update(
        profileId="direct:second",
        displayName="Second DAC — Direct",
        selected=False,
    )
    section.setProperty("profiles", [PY_PROFILE_ROWS[0], second])
    QApplication.processEvents()
    selector = _visual_item(window, "audioOutputProfileSelector")
    _click(window, selector)
    QTest.qWait(100)
    option = _visual_item(window, "audioOutputProfileSelector_option_1")
    assert option is not None
    _click(window, option)
    QApplication.processEvents()
    assert window.property("profileRequests") == 1
    assert window.property("requestedProfileId") == "direct:second"
    assert selector.property("currentIndex") == 0
    window.close()


def test_ui90r1_24_unavailable_profile_is_really_disabled(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    unavailable = dict(PY_PROFILE_ROWS[0])
    unavailable.update(
        available=False, actionEnabled=False, statusLabel="Selected · unavailable"
    )
    second = dict(PY_PROFILE_ROWS[0])
    second.update(
        profileId="direct:second", displayName="Second DAC — Direct", selected=False
    )
    section.setProperty("profiles", [unavailable, second])
    QApplication.processEvents()
    selector = _visual_item(window, "audioOutputProfileSelector")
    _click(window, selector)
    QTest.qWait(100)
    option = _visual_item(window, "audioOutputProfileSelector_option_0")
    assert option is not None and option.property("enabled") is False
    _click(window, option)
    assert window.property("profileRequests") == 0
    window.close()


def _profile_row(profile_id: str, *, selected=False, enabled=True):
    return {
        "profileId": profile_id,
        "stableDeviceId": f"usb:{profile_id}",
        "displayName": f"{profile_id} — Direct",
        "deviceName": profile_id,
        "pathLabel": "Direct",
        "available": enabled,
        "selected": selected,
        "actionEnabled": enabled,
        "statusLabel": "Selected · available" if selected else "Available",
    }


def _open_profile_selector_from_keyboard(window, selector):
    selector.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Space)
    QTest.qWait(100)
    QApplication.processEvents()
    assert selector.property("popupVisible") is True
    active = window.activeFocusItem()
    assert active is not None, "profile popup must own keyboard focus"


def test_ui90r11_13_16_profile_keyboard_emits_exact_intent_without_authority_shift(
    qapp,
) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    profiles = [
        _profile_row("direct:p1", selected=True),
        _profile_row("direct:p2"),
    ]
    section.setProperty("profiles", profiles)
    section.setProperty("selectedProfileId", "direct:p1")
    QApplication.processEvents()
    selector = _visual_item(window, "audioOutputProfileSelector")

    _open_profile_selector_from_keyboard(window, selector)
    QTest.keyClick(window, Qt.Key_Down)
    QApplication.processEvents()
    assert selector.property("keyboardIndex") == 1
    QTest.keyClick(window, Qt.Key_Return)
    QApplication.processEvents()

    assert window.property("profileRequests") == 1
    assert window.property("requestedProfileId") == "direct:p2"
    assert section.property("selectedProfileId") == "direct:p1"
    assert selector.property("currentIndex") == 0
    window.close()


def test_ui90r11_14_profile_keyboard_skips_disabled_profile(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    section.setProperty(
        "profiles",
        [
            _profile_row("direct:p1", selected=True),
            _profile_row("direct:p2", enabled=False),
            _profile_row("direct:p3"),
        ],
    )
    section.setProperty("selectedProfileId", "direct:p1")
    QApplication.processEvents()
    selector = _visual_item(window, "audioOutputProfileSelector")

    _open_profile_selector_from_keyboard(window, selector)
    QTest.keyClick(window, Qt.Key_Down)
    QApplication.processEvents()
    assert selector.property("keyboardIndex") == 2
    QTest.keyClick(window, Qt.Key_Return)
    QApplication.processEvents()

    assert window.property("profileRequests") == 1
    assert window.property("requestedProfileId") == "direct:p3"
    assert section.property("selectedProfileId") == "direct:p1"
    window.close()


def test_ui90r11_15_profile_keyboard_escape_cancels_and_restores_focus(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    section.setProperty(
        "profiles",
        [_profile_row("direct:p1", selected=True), _profile_row("direct:p2")],
    )
    section.setProperty("selectedProfileId", "direct:p1")
    QApplication.processEvents()
    selector = _visual_item(window, "audioOutputProfileSelector")

    _open_profile_selector_from_keyboard(window, selector)
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(250)
    QApplication.processEvents()

    assert selector.property("popupVisible") is False
    assert window.property("profileRequests") == 0
    assert section.property("selectedProfileId") == "direct:p1"
    assert selector.property("activeFocus") is True
    window.close()


def test_ui90r11_profile_selector_runtime_accessibility_contract(qapp) -> None:
    from PySide6.QtGui import QAccessible

    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    selector = _visual_item(window, "audioOutputProfileSelector")
    interface = QAccessible.queryAccessibleInterface(selector)

    assert interface is not None
    assert interface.role() == QAccessible.Role.ComboBox
    assert interface.text(QAccessible.Text.Name) == "Output profile"
    assert selector.property("focusPolicy") == Qt.StrongFocus
    window.close()


def test_ui90r1_25_failure_banner_is_visible_at_runtime(qapp) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    section.setProperty("lastFailureTitle", "Device disconnected")
    section.setProperty("lastFailureDisplay", "The selected DAC is unavailable.")
    QApplication.processEvents()
    banner = _visual_item(window, "audioOutputFailureBanner")
    assert banner is not None and banner.property("visible") is True
    assert banner.property("height") > 0
    window.close()


def _bounds_in(item, ancestor):
    origin = item.mapToItem(ancestor, QPointF(0, 0))
    return origin.x(), origin.y(), item.width(), item.height()


def _assert_settings_geometry(qapp, width: int) -> None:
    _engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    window.setProperty("width", width)
    QApplication.processEvents()
    section = _visual_item(window, "outputSettings")
    selector = _visual_item(window, "audioOutputProfileSelector")
    cards = _visual_item(window, "audioOutputDeviceCards")
    profile_copy = _visual_item(window, "audioOutputProfileCopy")
    assert section is not None and selector is not None and cards is not None
    sx, _sy, sw, sh = _bounds_in(selector, section)
    cx, _cy, cw, ch = _bounds_in(cards, section)
    tx, _ty, tw, th = _bounds_in(profile_copy, section)
    assert sw > 0 and sh > 0 and sx >= 0 and sx + sw <= section.width() + 1
    assert cw > 0 and ch > 0 and cx >= 0 and cx + cw <= section.width() + 1
    assert tw > 0 and th > 0 and tx + tw <= sx + 1
    window.close()


def test_ui90r1_26_settings_geometry_at_1920(qapp) -> None:
    _assert_settings_geometry(qapp, 1920)


def test_ui90r1_27_settings_geometry_at_1440(qapp) -> None:
    _assert_settings_geometry(qapp, 1440)


def test_ui90r1_28_settings_geometry_at_1280(qapp) -> None:
    _assert_settings_geometry(qapp, 1280)


def test_ui90r1_29_settings_geometry_at_980(qapp) -> None:
    _assert_settings_geometry(qapp, 980)


def _assert_now_playing_geometry(qapp, width: int) -> None:
    _engine, _component, window = _create(
        qapp, NOW_PLAYING_HARNESS, "tests/ui90r1-now-playing.qml"
    )
    window.setProperty("width", width)
    QApplication.processEvents()
    bar = _visual_item(window, "nowPlayingBar")
    track = _visual_item(window, "trackCard")
    playback = _visual_item(window, "playbackZone")
    output = _visual_item(window, "outputZone")
    assert all(item is not None for item in (bar, track, playback, output))
    tx, ty, tw, th = _bounds_in(track, bar)
    px, py, pw, ph = _bounds_in(playback, bar)
    ox, oy, ow, oh = _bounds_in(output, bar)
    assert bar.height() == 154
    assert min(tw, th, pw, ph, ow, oh) > 0
    assert tx >= 0 and tx + tw <= px + 1
    assert px + pw <= ox + 1
    assert ox + ow <= bar.width() + 1
    assert min(ty, py, oy) >= 0
    assert max(ty + th, py + ph, oy + oh) <= bar.height() + 1
    window.close()


def test_ui90r1_30_now_playing_geometry_at_1920(qapp) -> None:
    _assert_now_playing_geometry(qapp, 1920)


def test_ui90r1_31_now_playing_geometry_at_1440(qapp) -> None:
    _assert_now_playing_geometry(qapp, 1440)


def test_ui90r1_32_now_playing_geometry_at_1280(qapp) -> None:
    _assert_now_playing_geometry(qapp, 1280)


def test_ui90r1_33_now_playing_geometry_at_980(qapp) -> None:
    _assert_now_playing_geometry(qapp, 980)


def test_ui90r1_34_settings_runtime_transitions_emit_no_qml_warnings(qapp) -> None:
    engine, _component, window = _create(qapp, SETTINGS_HARNESS, "tests/ui90.qml")
    section = window.findChild(QObject, "outputSettings")
    unavailable = dict(PY_PROFILE_ROWS[0])
    unavailable.update(
        available=False, actionEnabled=False, statusLabel="Selected · unavailable"
    )
    section.setProperty("profiles", [unavailable])
    section.setProperty("lastFailureTitle", "Device disconnected")
    section.setProperty("lastFailureDisplay", "The selected DAC is unavailable.")
    section.setProperty("profiles", PY_PROFILE_ROWS)
    section.setProperty("lastFailureTitle", "")
    QApplication.processEvents()
    assert engine._michi_test_warnings == []
    window.close()


def test_ui90r1_35_popup_hotplug_transitions_emit_no_qml_warnings(qapp) -> None:
    engine, _component, window = _create(qapp, POPUP_HARNESS, "tests/ui90.qml")
    popup = _open_popup(window)
    disconnected = dict(PY_DEVICE_ROW)
    disconnected.update(
        available=False, canSelect=False, statusLabel="Selected · unavailable"
    )
    popup.setProperty("devices", [PY_SHARED_ROW, disconnected])
    popup.setProperty("devices", [PY_SHARED_ROW, PY_DEVICE_ROW])
    QTest.keyClick(window, Qt.Key_Escape)
    QApplication.processEvents()
    assert engine._michi_test_warnings == []
    window.close()


def test_ui90r1_36_now_playing_runtime_height_remains_154(qapp) -> None:
    _engine, _component, window = _create(
        qapp, NOW_PLAYING_HARNESS, "tests/ui90r1-now-playing.qml"
    )
    bar = _visual_item(window, "nowPlayingBar")
    assert bar.property("implicitHeight") == 154
    assert bar.height() == 154
    window.close()


def test_ui90r1_37_playback_controls_remain_visible_and_non_overlapping(qapp) -> None:
    _engine, _component, window = _create(
        qapp, NOW_PLAYING_HARNESS, "tests/ui90r1-now-playing.qml"
    )
    window.setProperty("width", 980)
    QApplication.processEvents()
    bar = _visual_item(window, "nowPlayingBar")
    previous = _visual_item(window, "previousButton")
    play_pause = _visual_item(window, "playPauseButton")
    next_button = _visual_item(window, "nextButton")
    output = _visual_item(window, "outputZone")
    for item in (previous, play_pause, next_button, output):
        assert item is not None and item.property("visible") is True
        assert item.width() > 0 and item.height() > 0
    px, _py, pw, _ph = _bounds_in(play_pause, bar)
    ox, _oy, _ow, _oh = _bounds_in(output, bar)
    assert px + pw <= ox
    window.close()
