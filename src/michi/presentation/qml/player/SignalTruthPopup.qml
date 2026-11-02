import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"
import "../controls"
import "../primitives"
import "../theme"

// F11 Signal Truth surface. It renders the canonical projection only; it never
// infers HD, bit-perfect, DSD preservation or DoP verification from labels.
Popup {
    id: root
    objectName: "SignalTruthPopup"
    property var signalPathBridge: null
    property var focusReturnTarget: null
    signal configurationAction(string action)

    readonly property var stages: signalPathBridge ? signalPathBridge.stages : []
    readonly property string headline: signalPathBridge
        ? signalPathBridge.headline : qsTr("Not verified")
    readonly property string proofLevel: signalPathBridge
        ? signalPathBridge.proofLevel : qsTr("Not verified")

    function bridgeValue(name, fallback) {
        if (!signalPathBridge)
            return fallback
        var value = signalPathBridge[name]
        return value === undefined ? fallback : value
    }

    padding: MichiSpacing.lg
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    // The opener is a small capsule; the popup must measure the window
    // overlay, never its parent item, or the Signal Truth surface collapses.
    width: Math.max(400, Math.min(440, (Overlay.overlay
        ? Overlay.overlay.width : 480) - 24))
    enter: Transition {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation {
            property: "opacity"
            from: 0
            to: 1
            duration: MichiMotion.popupOpen
            easing.type: MichiMotion.outCubic
        }
    }
    exit: Transition {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation {
            property: "opacity"
            from: 1
            to: 0
            duration: MichiMotion.popupClose
            easing.type: MichiMotion.outCubic
        }
    }
    background: MichiGlassSurface {
        elevation: "elevated"
        contentPadding: 0
        tileSeed: 17
        materialOpacityOverride: 1.0
    }

    onOpened: closeButton.forceActiveFocus()
    onClosed: if (focusReturnTarget) focusReturnTarget.forceActiveFocus()

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiPopupHeader {
            iconName: "output-status"
            title: qsTr("Signal Truth")
            subtitle: qsTr("Actual audio signal path")
            badgeText: root.proofLevel
            badgeTone: root.bridgeValue("headlineTone", "neutral") === "warning"
                ? "warning"
                : root.bridgeValue("headlineTone", "neutral") === "error"
                    ? "error" : "neutral"
        }

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                text: root.headline
                role: "body"
                color: root.bridgeValue("headlineTone", "neutral") === "error"
                    ? MichiPalette.error
                    : root.bridgeValue("headlineTone", "neutral") === "warning"
                        ? MichiPalette.warning : MichiPalette.textPrimary
                Layout.fillWidth: true
            }
            MichiButton {
                id: closeButton
                text: qsTr("Close")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlSmall
                onClicked: root.close()
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: root.stages
                delegate: MichiSignalNode {
                    required property var modelData
                    Layout.fillWidth: true
                    iconName: modelData.id === "source" ? "track"
                        : modelData.id === "decode" ? "audio-engine"
                        : modelData.id === "processing" ? "equalizer"
                        : modelData.id === "output" ? "audio-output"
                        : "device"
                    title: modelData.title
                    summary: modelData.summary
                    detail: modelData.detail
                    configAction: modelData.configAction
                    stageState: modelData.state
                    onConfigurationRequested: action => {
                        root.close()
                        if (root.signalPathBridge)
                            root.signalPathBridge.request_configuration(action)
                        root.configurationAction(action)
                    }
                }
            }
        }

        MichiPopupFooter {
            note: qsTr("Proof scope · %1").arg(root.proofLevel)
            MichiText {
                text: qsTr("Observed facts only")
                role: "micro"
                color: MichiPalette.textMuted
            }
        }
    }
}
