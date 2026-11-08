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

    readonly property var canonicalTruthFrame: signalPathBridge
        && signalPathBridge.truthFrame ? signalPathBridge.truthFrame : ({})
    // Prefer the canonical F03/owner frame; legacy projections without one
    // keep the established bridge stages instead of collapsing the popup.
    readonly property var stages: {
        const canonicalStages = canonicalTruthFrame.stages
        if (canonicalStages && canonicalStages.length > 0)
            return canonicalStages
        return signalPathBridge ? signalPathBridge.stages : []
    }
    readonly property string headline: signalPathBridge
        ? signalPathBridge.headline : qsTr("No active path")
    readonly property string proofLevel: signalPathBridge
        ? signalPathBridge.proofLevel : qsTr("Not verified")
    readonly property string statusLabel: signalPathBridge
        ? signalPathBridge.statusLabel : qsTr("No active path")
    readonly property string temporalStatus: signalPathBridge
        ? signalPathBridge.status : "NONE"
    readonly property string temporalBadge: signalPathBridge
        ? signalPathBridge.status === "ACTIVE" ? qsTr("LIVE")
        : signalPathBridge.status === "HISTORICAL" ? qsTr("LAST PLAYBACK")
        : signalPathBridge.status === "PENDING" ? qsTr("PREPARING")
        : qsTr("NOT ACTIVE")
        : qsTr("NOT ACTIVE")
    readonly property string familyEvidenceText: canonicalTruthFrame.familyEvidenceText || ""
    readonly property string dspExecutionText: canonicalTruthFrame.dspExecutionText || ""
    readonly property string familyEvidenceState: canonicalTruthFrame.familyEvidenceState || "UNOBSERVED"
    readonly property var metricItems: signalPathBridge
        ? signalPathBridge.metricItems : []
    readonly property string proofState: signalPathBridge
        ? signalPathBridge.pathProofState : "no_path"
    readonly property string proofLabel: signalPathBridge
        ? signalPathBridge.pathProofLabel : qsTr("No verified path")
    readonly property string proofTone: proofState === "verified" ? "success"
        : proofState === "contradicted" ? "error"
        : proofState === "partially_verified" ? "warning"
        : proofState === "pending" ? "active"
        : "neutral"
    readonly property string sourceLine: signalPathBridge
        ? signalPathBridge.sourceFormatLabel + " · "
            + signalPathBridge.sourceRateDepthLabel
        : qsTr("NO TRACK")
    readonly property string indicatorState: signalPathBridge
        ? signalPathBridge.indicatorState : "none"
    readonly property string indicatorTooltip: signalPathBridge
        ? signalPathBridge.indicatorTooltip : qsTr("Signal Truth: no active playback")
    readonly property string expandedKey: signalPathBridge
        ? "stage:" + signalPathBridge.generation : "stage:0"
    property string expandedStageId: ""
    // The opener injects the space that actually exists above the badge. It
    // bounds the intrinsic height in short windows so the fixed footer and the
    // 8 px anchor gap can never overlap the NowPlaying bar.
    property real maxPopupHeight: 0
    // Intrinsic, content-led geometry. A five-stage path must be fully legible
    // without scrolling. Compact only when the actual viewport is short.
    readonly property real safeOverlayHeight: Math.max(0,
        (Overlay.overlay ? Overlay.overlay.height : 768) - 2 * MichiSpacing.md)
    readonly property bool compactDensity: safeOverlayHeight < 680
    readonly property real stageAvailableHeight: Math.min(safeOverlayHeight,
        maxPopupHeight > 0 ? maxPopupHeight : safeOverlayHeight)
    // Header + summary card + headline + footer + spacing. The stage area is
    // the only region allowed to shrink; the footer must stay visible.
    readonly property real chromeHeight: (compactDensity ? 220 : 252)
        + (temporalStatus === "ACTIVE" && familyEvidenceText !== "" ? 30 : 0)
        + (temporalStatus === "ACTIVE" && metricItems && metricItems.length > 0 ? 32 : 0)
    readonly property real stageViewportLimit: Math.max(120,
        stageAvailableHeight - chromeHeight)
    // Deterministic content budget from the stage view's intrinsic height.
    // Never derive popup height from the popup's own contentItem height: that
    // closes a binding loop through the Layout height negotiation.
    readonly property real desiredHeight: chromeHeight
        + Math.min(stageView.implicitHeight, stageViewportLimit)
        + topPadding + bottomPadding

    padding: compactDensity ? MichiSpacing.lg : MichiSpacing.lg + MichiSpacing.xs
    // P0 KX11-16: modal overlay absorbs pointer presses BEFORE the library's
    // TrackRow TapHandler. dim:false retains the smoked Michi presentation.
    // Never revert to modal:false without a real background-click isolation test.
    modal: true
    dim: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    // The stage list determines height: 5 rows ~600px, not a fixed 520px.
    // The overlay bounds are a safety limit, NOT the preferred size.
    width: Math.max(440, Math.min(500, (Overlay.overlay
        ? Overlay.overlay.width : 500) - 24))
    height: Math.min(680, safeOverlayHeight,
        maxPopupHeight > 0 ? maxPopupHeight : safeOverlayHeight,
        Math.ceil(desiredHeight))

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
        allowBackdropBlur: false
    }

    onOpened: {
        root.expandedStageId = ""
        Qt.callLater(stageView.focusFirstStage)
    }
    onClosed: if (focusReturnTarget) focusReturnTarget.forceActiveFocus()
    onExpandedStageIdChanged: {
        if (expandedStageId !== "")
            Qt.callLater(function () {
                root.revealStage(expandedStageId)
            })
    }

    function revealStage(stageId) {
        const stage = stageView.stageItem(stageId)
        if (!stage) return
        const limit = Math.max(0,
            stageView.implicitHeight - stagesViewport.height)
        stagesViewport.contentY = Math.max(0,
            Math.min(stage.y - MichiSpacing.sm, limit))
    }

    contentItem: ColumnLayout {
        id: panel
        spacing: root.compactDensity ? MichiSpacing.sm : MichiSpacing.md

        MichiPopupHeader {
            iconName: "output-status"
            title: qsTr("SIGNAL TRUTH")
            subtitle: qsTr("Actual audio signal path")
            badgeText: root.temporalBadge
            badgeTone: root.temporalStatus === "ACTIVE" ? "success"
                : root.temporalStatus === "PENDING" ? "active"
                : "neutral"
        }

        Rectangle {
            id: summaryCard
            Layout.fillWidth: true
            implicitHeight: summaryColumn.implicitHeight
                + 2 * (root.compactDensity ? MichiSpacing.sm : MichiSpacing.md)
            radius: MichiRadius.lg
            color: MichiPalette.graphite
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle

            ColumnLayout {
                id: summaryColumn
                anchors.fill: parent
                anchors.margins: root.compactDensity
                    ? MichiSpacing.sm : MichiSpacing.md
                spacing: MichiSpacing.xs

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiQualityDot {
                        Layout.alignment: Qt.AlignVCenter
                        diameter: 8
                        qualityClass: root.signalPathBridge
                            ? root.signalPathBridge.sourceQualityClass : "unknown"
                    }
                    MichiText {
                        text: root.sourceLine
                        role: "body"
                        font.weight: Font.DemiBold
                        color: MichiPalette.textPrimary
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    MichiStatusChip {
                        visible: root.temporalStatus !== "HISTORICAL"
                        text: root.proofLabel
                        tone: root.proofTone
                        dotVisible: false
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiSignalIndicator {
                        indicatorState: root.indicatorState
                        tooltip: root.indicatorTooltip
                        Layout.alignment: Qt.AlignTop
                        Layout.topMargin: 2
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

                MichiText {
                    visible: root.temporalStatus === "ACTIVE"
                        && root.familyEvidenceText !== ""
                    text: root.familyEvidenceText
                    role: "caption"
                    color: root.familyEvidenceState === "CONFLICTED"
                        ? MichiPalette.error : MichiPalette.textSecondary
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    Accessible.name: root.familyEvidenceText
                }

                // A49: a bounded owner-thread projection timing disclosure;
                // NOT an audio callback latency or a DAC/bit-perfect claim.
                MichiSignalTruthMetrics {
                    objectName: "signalTruthMetricsDisclosure"
                    Layout.fillWidth: true
                    compact: root.compactDensity
                    temporalStatus: root.temporalStatus
                    metricItems: root.metricItems
                    visible: root.temporalStatus === "ACTIVE"
                        && root.metricItems && root.metricItems.length > 0
                }
            }
        }

        // No persistent ScrollView: the popup grows with the real stage count
        // and disclosure height. Flicking activates ONLY as an emergency
        // fallback when a small viewport cannot physically hold all evidence.
        Flickable {
            id: stagesViewport
            objectName: "signalTruthStagesViewport"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(stageView.implicitHeight,
                root.stageViewportLimit)
            Layout.maximumHeight: root.stageViewportLimit
            contentWidth: width
            contentHeight: stageView.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentHeight > height + 1
            clip: interactive
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            Accessible.name: qsTr("Signal stages; full path is visible unless the window is too short")

            MichiSignalPathView {
                id: stageView
                objectName: "signalTruthStageView"
                width: stagesViewport.width
                compact: root.compactDensity
                // Compact density must not silently remove configuration tools.
                configurationEnabled: true
                stages: root.stages
                expandedStageId: root.expandedStageId
                onExpansionRequested: stageId => { root.expandedStageId = stageId }
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
        }
    }
}
