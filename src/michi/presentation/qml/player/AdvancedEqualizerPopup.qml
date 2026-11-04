import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"
import "../controls"
import "../primitives"
import "../theme"

// F11 Expert surface: precision sound shaping. Every feature is gated by the
// processing authority; unavailable tabs explain the blocker instead of
// rendering dead controls.
Popup {
    id: root
    objectName: "AdvancedEqualizerPopup"
    property var processingBridge: null
    property var focusReturnTarget: null
    property string activeTab: "graphic"
    readonly property bool editableTab: activeTab === "graphic" || activeTab === "parametric" || activeTab === "profiles"
    readonly property bool pendingDraft: bridgeValue("draftDirty", false)
    readonly property bool canCommit: editableTab && pendingDraft && bridgeValue("canApply", false)
    readonly property var tabs: [
        {"id": "graphic", "label": qsTr("Graphic 10")},
        {"id": "parametric", "label": qsTr("PEAK 10")},
        {"id": "convolution", "label": qsTr("FIR status")},
        {"id": "signal", "label": qsTr("Signal status")},
        {"id": "profiles", "label": qsTr("Presets")}
    ]
    readonly property var bands: processingBridge ? processingBridge.bands : []
    readonly property string effectiveState: processingBridge
        ? processingBridge.effectiveState : "unavailable"
    readonly property bool busy: bridgeValue("busy", false)
    readonly property bool dirty: bridgeValue("draftDirty", false)
    readonly property string errorCode: bridgeValue("errorCode", "")
    readonly property string workspaceState: errorCode !== "" ? "failed"
        : busy ? (dirty ? "applying" : "validating")
        : dirty ? "draft"
        : effectiveState
    readonly property string stateLabel: workspaceState === "draft" ? qsTr("Draft")
        : workspaceState === "validating" ? qsTr("Validating")
        : workspaceState === "applying" ? qsTr("Applying")
        : workspaceState === "effective" ? qsTr("Effective · revision %1")
            .arg(root.bridgeValue("committedRevision", 0))
        : workspaceState === "bypassed" ? qsTr("Bypassed")
        : workspaceState === "failed" ? qsTr("Failed")
        : qsTr("Unavailable")
    readonly property string stateTone: workspaceState === "effective" ? "success"
        : workspaceState === "failed" ? "error"
        : workspaceState === "unavailable" ? "warning"
        : workspaceState === "applying" || workspaceState === "validating"
            ? "active" : "neutral"

    function responseLegend() {
        if (!processingBridge)
            return qsTr("Calculated response")
        if (bridgeValue("effectiveState", "unknown") === "unavailable")
            return qsTr("Calculated response · unavailable")
        if (bridgeValue("draftDirty", false))
            return qsTr("Calculated response · draft")
        if (bridgeValue("effectiveState", "unknown") === "bypassed")
            return qsTr("Calculated response · bypassed")
        return qsTr("Calculated response · applied")
    }

    function bridgeValue(name, fallback) {
        if (!processingBridge)
            return fallback
        var value = processingBridge[name]
        return value === undefined ? fallback : value
    }

    padding: MichiSpacing.lg
    // Never let background TrackRow TapHandlers activate when editing.
    modal: true
    dim: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    // Advanced EQ is centred in the scene, so the window overlay owns both
    // dimensions. Binding to the opener clipped the whole surface to 2 px.
    width: Math.max(320, Math.min(960, (Overlay.overlay
        ? Overlay.overlay.width : 960) - 32))
    height: Math.max(360, Math.min(700, (Overlay.overlay
        ? Overlay.overlay.height : 700) - 32))
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
        tileSeed: 15
        materialOpacityOverride: 1.0
    }

    onOpened: {
        if (processingBridge)
            processingBridge.refresh()
        tabBar.forceActiveFocus()
    }
    onClosed: if (focusReturnTarget) focusReturnTarget.forceActiveFocus()

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiPopupHeader {
            iconName: "sliders"
            Layout.minimumHeight: 68
            title: qsTr("Advanced Equalizer")
            subtitle: qsTr("10-band editing · readback-first DSP")
            badgeText: root.stateLabel
            badgeTone: root.stateTone
        }

        Flow {
            id: tabBar
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            spacing: 0
            Repeater {
                model: root.tabs
                delegate: MichiButton {
                    required property var modelData
                    text: modelData.label
                    variant: "ghost"
                    implicitHeight: MichiMetrics.controlMedium
                    selected: root.activeTab === modelData.id
                    onClicked: root.activeTab = modelData.id
                }
            }
        }

        MichiText {
            visible: root.errorCode !== ""
            Layout.fillWidth: true
            text: root.bridgeValue("errorMessage", root.errorCode)
            role: "caption"
            color: MichiPalette.error
            wrapMode: Text.WordWrap
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: Math.max(0, root.tabs.findIndex(function (tab) {
                return tab.id === root.activeTab
            }))

            // Graphic: the backend contract is not proven. A compact blocker
            // replaces the previous 31 dead chips.
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.md
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        radius: MichiRadius.lg
                        color: MichiPalette.smoke
                        border.width: 1
                        border.color: MichiSemanticColors.borderSubtle
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: MichiSpacing.md
                            spacing: MichiSpacing.md
                            MichiIcon {
                                name: "equalizer"
                                width: 20
                                height: 20
                                iconColor: MichiPalette.warning
                            }
                            MichiText {
                                text: qsTr("ISO-31 awaits host readback. The ten rails below edit the real PCM DSP draft.")
                                role: "secondary"
                                color: MichiPalette.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(240,
                            Math.max(180, root.height * 0.32))
                        MichiEqResponsePlot {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 40 + 10 * 56 + 9 * MichiSpacing.xs
                            height: parent.height
                            points: root.bridgeValue("responseCurve", [])
                            sampleRate: 0
                            legendText: root.responseLegend()
                        }
                    }
                    Item {
                        objectName: "graphicRailsHost"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        RowLayout {
                            objectName: "graphicRailsRow"
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 40 + 10 * 56 + 9 * MichiSpacing.xs
                            height: parent.height
                            spacing: MichiSpacing.xs
                        Item {
                            Layout.preferredWidth: 40
                            Layout.fillHeight: true
                            MichiText {
                                anchors.top: parent.top
                                anchors.right: parent.right
                                text: qsTr("+12")
                                role: "micro"
                                color: MichiPalette.textMuted
                            }
                            MichiText {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.right: parent.right
                                text: qsTr("0")
                                role: "micro"
                                color: MichiPalette.textMuted
                            }
                            MichiText {
                                anchors.bottom: parent.bottom
                                anchors.right: parent.right
                                text: qsTr("−12")
                                role: "micro"
                                color: MichiPalette.textMuted
                            }
                        }
                        Repeater {
                            model: root.bands
                            delegate: MichiEqSlider {
                                required property var modelData
                                required property int index
                                objectName: "advancedGraphicBand_" + index
                                Layout.fillWidth: false
                                Layout.minimumWidth: 48
                                Layout.preferredWidth: 56
                                Layout.maximumWidth: 56
                                Layout.preferredHeight: 180
                                bandLabel: modelData.label
                                gainDb: modelData.gainDb
                                inactive: modelData.inactiveReason !== ""
                                inactiveReason: modelData.inactiveReason
                                enabled: root.bridgeValue("canEdit", false)
                                onGainCommitted: gain => {
                                    if (root.processingBridge)
                                        root.processingBridge.set_draft_band(index, gain)
                                }
                            }
                        }
                        }
                    }
                }
            }

            // Parametric: only the committed ten-band filter set is shown.
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.sm
                    MichiText {
                        text: qsTr("Parametric filters")
                        role: "section"
                    }
                    MichiText {
                        text: qsTr("Edit gain for ten real PEAK filters (fixed centres and Q=√2). Arbitrary frequency, type and Q are NOT supported yet.")
                        role: "secondary"
                        color: MichiPalette.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    MichiEqResponsePlot {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(240,
                            Math.max(220, root.height * 0.30))
                        points: root.bridgeValue("responseCurve", [])
                        sampleRate: 0
                        legendText: root.responseLegend()
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 28
                        spacing: MichiSpacing.md
                        MichiText { text: qsTr("ON"); role: "micro"; Layout.preferredWidth: 36 }
                        MichiText { text: qsTr("TYPE"); role: "micro"; Layout.preferredWidth: 120 }
                        MichiText { text: qsTr("FREQ"); role: "micro"; Layout.preferredWidth: 88 }
                        MichiText { text: qsTr("GAIN"); role: "micro"; Layout.fillWidth: true }
                        MichiText { text: qsTr("Q"); role: "micro"; Layout.preferredWidth: 68 }
                        MichiText { text: qsTr("FIXED"); role: "micro"; Layout.preferredWidth: 43 }
                    }
                    Repeater {
                        model: root.bands
                        delegate: RowLayout {
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            spacing: MichiSpacing.md
                            MichiText {
                                text: qsTr("On")
                                role: "micro"
                                color: MichiPalette.success
                                Layout.preferredWidth: 36
                            }
                            MichiText {
                                text: qsTr("PEAK")
                                role: "caption"
                                color: MichiPalette.textSecondary
                                Layout.preferredWidth: 120
                            }
                            MichiText {
                                text: modelData.label + " Hz"
                                role: "technical"
                                technical: true
                                Layout.preferredWidth: 88
                            }
                            MichiSlider {
                                objectName: "advancedPeqGain_" + index
                                Layout.fillWidth: true
                                from: -12
                                to: 12
                                stepSize: 0.5
                                value: modelData.gainDb
                                enabled: root.bridgeValue("canEdit", false) && modelData.enabled
                                accessibleName: qsTr("PEAK gain at %1 Hz").arg(modelData.label)
                                onMoved: {
                                    if (root.processingBridge)
                                        root.processingBridge.set_draft_band(index, value)
                                }
                            }
                            MichiText {
                                text: (modelData.gainDb >= 0 ? "+" : "")
                                    + modelData.gainDb.toFixed(1) + " dB"
                                role: "technical"
                                technical: true
                                Layout.preferredWidth: 68
                            }
                            MichiText {
                                text: qsTr("Fixed")
                                role: "micro"
                                color: MichiPalette.textMuted
                                Layout.preferredWidth: 43
                            }
                        }
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.md
                    MichiText { text: qsTr("Convolution / FIR"); role: "section" }
                    MichiText {
                        text: qsTr("No impulse-response asset authority is connected. Import, hashes, latency and readback stay disabled until the backend can prove them.")
                        role: "secondary"
                        color: MichiPalette.warning
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.md
                    MichiText { text: qsTr("Signal / Resampling"); role: "section" }
                    GridLayout {
                        columns: 2
                        columnSpacing: MichiSpacing.xl
                        rowSpacing: MichiSpacing.sm
                        MichiText { text: qsTr("Processing state"); role: "caption" }
                        MichiText { text: root.effectiveState; role: "technical" }
                        MichiText { text: qsTr("Source family"); role: "caption" }
                        MichiText {
                            text: root.bridgeValue("sourceFamily", "unknown")
                            role: "technical"
                        }
                        MichiText { text: qsTr("Requested revision"); role: "caption" }
                        MichiText {
                            text: String(root.bridgeValue("requestRevision", 0))
                            role: "technical"
                        }
                        MichiText { text: qsTr("Effective revision"); role: "caption" }
                        MichiText {
                            text: String(root.bridgeValue("committedRevision", 0))
                            role: "technical"
                        }
                    }
                    MichiText {
                        text: qsTr("Resampling and dither are controlled by the output path. This surface never changes bit depth or DSD mode.")
                        role: "secondary"
                        color: MichiPalette.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.md
                    MichiText { text: qsTr("Profiles"); role: "section" }
                    Repeater {
                        model: root.processingBridge ? root.processingBridge.factoryPresets : []
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            spacing: MichiSpacing.md
                            MichiText {
                                text: modelData.displayName || modelData.id || ""
                                role: "body"
                                Layout.fillWidth: true
                            }
                            MichiStatusChip {
                                text: root.bridgeValue("presetId", "") === modelData.id
                                    ? qsTr("Selected draft") : qsTr("Available")
                                tone: root.bridgeValue("presetId", "") === modelData.id
                                    ? "active" : "neutral"
                                dotVisible: false
                            }
                            MichiButton {
                                text: qsTr("Load to draft")
                                variant: "ghost"
                                enabled: root.bridgeValue("canEdit", false)
                                accessibleName: qsTr("Load %1 into EQ draft").arg(modelData.displayName)
                                onClicked: {
                                    if (root.processingBridge)
                                        root.processingBridge.select_preset(modelData.id)
                                }
                            }
                        }
                    }
                    MichiText {
                        text: qsTr("Create, rename, duplicate, delete and output association require a profile repository capability that is not composed in this sprint.")
                        role: "secondary"
                        color: MichiPalette.warning
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        MichiPopupFooter {
            note: root.editableTab
                ? qsTr("Edits are drafts until Apply confirms host readback")
                : qsTr("Inspection only · no DSP changes")
            MichiButton {
                text: qsTr("Discard draft")
                variant: "ghost"
                visible: root.editableTab
                enabled: root.pendingDraft && !root.bridgeValue("busy", false)
                onClicked: {
                    if (root.processingBridge)
                        root.processingBridge.discard_draft()
                }
            }
            MichiButton {
                text: qsTr("Validate")
                variant: "ghost"
                visible: root.editableTab
                enabled: root.pendingDraft && !root.bridgeValue("busy", false)
                onClicked: {
                    if (root.processingBridge)
                        root.processingBridge.validate_draft()
                }
            }
            MichiButton {
                text: qsTr("Apply draft")
                visible: root.editableTab
                enabled: root.canCommit
                onClicked: {
                    if (root.processingBridge && root.canCommit)
                        root.processingBridge.apply_draft_async()
                }
            }
        }
    }
}
