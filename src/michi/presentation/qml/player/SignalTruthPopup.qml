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
        ? signalPathBridge.headline : qsTr("No active path")
    readonly property string proofLevel: signalPathBridge
        ? signalPathBridge.proofLevel : qsTr("Not verified")
    readonly property string statusLabel: signalPathBridge
        ? signalPathBridge.statusLabel : qsTr("No active path")
    readonly property string indicatorState: signalPathBridge
        ? signalPathBridge.indicatorState : "none"
    readonly property string indicatorTooltip: signalPathBridge
        ? signalPathBridge.indicatorTooltip : qsTr("Signal Truth: no active playback")
    readonly property string expandedKey: signalPathBridge
        ? "stage:" + signalPathBridge.generation : "stage:0"
    property string expandedStageId: ""

    padding: MichiSpacing.lg
    // P0 KX11-16: modal overlay absorbs pointer presses BEFORE the library's
    // TrackRow TapHandler. dim:false retains the smoked Michi presentation.
    // Never revert to modal:false without a real background-click isolation test.
    modal: true
    dim: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    // Position is still anchored to the quality capsule, but size belongs to
    // the window overlay, never the 34px opener.
    width: Math.max(320, Math.min(480, (Overlay.overlay
        ? Overlay.overlay.width : 480) - 24))
    // Five rows should not create a 760px empty column in the audio inspector.
    // Larger disclosures scroll inside the bounded viewport.
    height: Math.min(560, Math.max(0, (Overlay.overlay
        ? Overlay.overlay.height : 584) - 24))

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

    onOpened: {
        root.expandedStageId = ""
        closeButton.forceActiveFocus()
    }
    onClosed: if (focusReturnTarget) focusReturnTarget.forceActiveFocus()

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiPopupHeader {
            iconName: "output-status"
            title: qsTr("Signal Truth")
            subtitle: qsTr("Observed signal path")
            badgeText: root.statusLabel
            badgeTone: root.indicatorState === "error" ? "error"
                : root.indicatorState === "pending" ? "active"
                : root.indicatorState === "observed"
                    || root.indicatorState === "transformed" ? "success"
                : "neutral"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiSignalIndicator {
                indicatorState: root.indicatorState
                tooltip: root.indicatorTooltip
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 3
            }
            MichiText {
                text: root.headline
                role: "body"
                font.weight: Font.DemiBold
                color: root.indicatorState === "error" ? MichiPalette.error
                    : root.indicatorState === "pending" ? MichiPalette.auroraBlue
                    : MichiPalette.textPrimary
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }

        ScrollView {
            id: stagesScroll
            objectName: "signalTruthStagesScroll"
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            MichiSignalPathView {
                width: stagesScroll.availableWidth
                stages: root.stages
                expandedStageId: root.expandedStageId
                onConfigurationRequested: action => {
                    root.close()
                    if (root.signalPathBridge)
                        root.signalPathBridge.request_configuration(action)
                    root.configurationAction(action)
                }
            }
        }

        MichiPopupFooter {
            note: qsTr("Proof scope · %1").arg(root.proofLevel)
            MichiButton {
                id: closeButton
                text: qsTr("Close")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlSmall
                onClicked: root.close()
            }
        }
    }
}
