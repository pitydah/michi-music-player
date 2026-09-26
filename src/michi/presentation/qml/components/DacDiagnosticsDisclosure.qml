import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    property var device: ({})
    property var signalPath: []
    property var reasonCodes: []
    property string signalTruthLabel: qsTr("Not verified")
    property bool expanded: false
    spacing: MichiSpacing.sm

    Button {
        id: toggle
        objectName: "dacAdvancedToggle_" + (root.device.stableDeviceId || "shared")
        Layout.fillWidth: true
        implicitHeight: 34
        focusPolicy: Qt.StrongFocus
        hoverEnabled: true
        padding: 0
        onClicked: root.expanded = !root.expanded
        Keys.onReturnPressed: toggle.clicked()
        Keys.onEnterPressed: toggle.clicked()
        Accessible.name: root.expanded
            ? qsTr("Hide advanced DAC diagnostics")
            : qsTr("Advanced DAC diagnostics")

        contentItem: MichiText {
            text: root.expanded
                ? qsTr("Hide advanced DAC diagnostics")
                : qsTr("Advanced DAC diagnostics")
            role: "secondary"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: MichiRadius.sm
            color: toggle.hovered ? MichiSemanticColors.surfaceHover : "transparent"
            border.width: toggle.visualFocus ? 1 : 0
            border.color: MichiSemanticColors.focusRing
        }
    }

    ColumnLayout {
        id: technicalContent
        objectName: "dacAdvancedContent_" + (root.device.stableDeviceId || "shared")
        visible: root.expanded
        Layout.fillWidth: true
        spacing: MichiSpacing.xs

        SignalTruthPanel {
            Layout.fillWidth: true
            verdictLabel: root.signalTruthLabel
            stages: root.signalPath
            reasonCodes: root.reasonCodes
        }

        MichiDivider { Layout.fillWidth: true }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Identity: %1 · %2")
                .arg(root.device.manufacturer || qsTr("Unknown manufacturer"))
                .arg(root.device.product || qsTr("Unknown model"))
            role: "technical"
            technical: true
            wrapMode: Text.WordWrap
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Class: %1 · confidence %2")
                .arg(root.device.deviceCategoryLabel || qsTr("Audio"))
                .arg(root.device.classificationConfidence || "—")
            role: "technical"
            technical: true
            wrapMode: Text.WordWrap
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Playback endpoints: %1 · capture capability: %2")
                .arg(root.device.playbackEndpointCount || 0)
                .arg(root.device.captureCapable ? qsTr("yes") : qsTr("no / not observed"))
            role: "technical"
            technical: true
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Qualified playback capabilities: %1")
                .arg(root.device.qualifiedCapabilitySummary || qsTr("Not yet qualified"))
            role: "technical"
            technical: true
            wrapMode: Text.WordWrap
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Stable device ID: %1").arg(root.device.shortenedStableDeviceId || "—")
            role: "technical"
            technical: true
            wrapMode: Text.WrapAnywhere
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Current ALSA endpoint: %1").arg(root.device.alsaLocator || "—")
            role: "technical"
            technical: true
            wrapMode: Text.WrapAnywhere
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("USB: VID %1 · PID %2 · bcdDevice %3")
                .arg(root.device.vendorId || "—")
                .arg(root.device.productId || "—")
                .arg(root.device.bcdDevice || "—")
            role: "technical"
            technical: true
            wrapMode: Text.WordWrap
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Identity confidence: %1 · binding generation %2")
                .arg(root.device.identityConfidence || "—")
                .arg(root.device.generation || 0)
            role: "technical"
            technical: true
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Capability evidence: %1")
                .arg(root.device.capabilityEvidenceLabel || qsTr("Unknown"))
            role: "technical"
            technical: true
        }
        MichiText {
            visible: (root.device.environmentFingerprint || "") !== ""
            Layout.fillWidth: true
            text: qsTr("Environment: %1").arg(root.device.environmentFingerprint)
            role: "technical"
            technical: true
            wrapMode: Text.WrapAnywhere
        }
        MichiText {
            visible: (root.device.runtimeSinkSummary || "") !== ""
            Layout.fillWidth: true
            text: qsTr("Runtime sink graph: %1").arg(root.device.runtimeSinkSummary)
            role: "technical"
            technical: true
            wrapMode: Text.WordWrap
        }
        MichiText {
            visible: (root.device.lastFailureCode || "") !== ""
            Layout.fillWidth: true
            text: qsTr("Last typed failure: %1").arg(root.device.lastFailureCode)
            role: "technical"
            technical: true
            wrapMode: Text.WordWrap
        }
    }
}
