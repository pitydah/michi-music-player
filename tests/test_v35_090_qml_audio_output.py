"""DAC-V35-090 UI90-22..47 — real QML audio-output presentation gates."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

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
        width: 900
        devices: harness.rows
        signalPath: harness.pathRows
        signalTruthReasonCodes: ["RUNTIME_EVIDENCE_INCOMPLETE"]
        canUseDirect: true
        onDeviceSelectionRequested: harness.deviceRequests++
        onSharedSelectionRequested: harness.sharedRequests++
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
        AudioOutputPopup {{
            id: popup
            objectName: "outputPopup"
            x: 40
            y: 40
            devices: harness.rows
            onDeviceSelectionRequested: harness.deviceRequests++
            onSharedSelectionRequested: harness.sharedRequests++
            onSettingsRequested: harness.settingsRequests++
        }}
    }}
    Component.onCompleted: popup.open()
}}
"""


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _create(qapp, code: str, base_rel: str):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.setData(code.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / base_rel)))
    assert component.status() == QQmlComponent.Ready, component.errorString()
    window = component.create()
    assert window is not None, component.errorString()
    section = window.findChild(QObject, "outputSettings")
    if section is not None:
        section.setProperty("devices", [PY_SHARED_ROW, PY_DEVICE_ROW])
        section.setProperty("signalPath", PY_PATH_ROWS)
    popup = window.findChild(QObject, "outputPopup")
    if popup is not None:
        popup.setProperty("devices", [PY_SHARED_ROW, PY_DEVICE_ROW])
    window.show()
    for _ in range(10):
        QApplication.processEvents()
    return engine, component, window


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
