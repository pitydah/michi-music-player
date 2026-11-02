import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"
import "../controls"
import "../primitives"
import "../theme"

// F11 Focused surface: ten-band quick EQ. Draft edits stay local until the
// bridge validates/prepares/commits through the processing authority.
Popup {
    id: root
    objectName: "EqualizerPopup"
    property var processingBridge: null
    property var focusReturnTarget: null
    property bool showResponse: false
    signal advancedRequested()

    readonly property bool available: processingBridge
        ? processingBridge.available : false
    readonly property bool controlsEnabled: available
        && !(processingBridge && processingBridge.busy)
    readonly property var bands: processingBridge
        ? processingBridge.bands : []
    readonly property var presets: processingBridge
        ? processingBridge.factoryPresets : []
    readonly property string errorText: processingBridge
        ? processingBridge.errorMessage : ""

    function bridgeValue(name, fallback) {
        if (!processingBridge)
            return fallback
        var value = processingBridge[name]
        return value === undefined ? fallback : value
    }

    function commitDraft() {
        // Draft edits stay local; this is the single commit boundary used by
        // every quick-EQ control that has a complete value to apply.
        if (processingBridge)
            processingBridge.apply_draft_async()
    }

    function closeAllSurfaces() {
        if (advancedPopup.opened)
            advancedPopup.close()
        if (opened)
            close()
    }

    padding: MichiSpacing.lg
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    // Popup.parent is the opener button, not the window. Sizing against the
    // opener produced a 10 px surface on the real Wayland shell, so the window
    // overlay is the only valid width authority for a focused popup.
    width: Math.max(420, Math.min(440, (Overlay.overlay
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
        tileSeed: 13
        radius: MichiRadius.floating
        // Focused surfaces stay legible over a busy library: smoked glass,
        // never a milky or fully transparent sheet.
        materialOpacityOverride: 1.0
    }

    onOpened: {
        if (advancedPopup.opened)
            advancedPopup.close()
        if (processingBridge)
            processingBridge.refresh()
        Qt.callLater(function () {
            for (var i = 0; i < railRepeater.count; ++i) {
                var rail = railRepeater.itemAt(i)
                if (rail && rail.enabled) {
                    rail.forceActiveFocus()
                    break
                }
            }
        })
    }
    onClosed: {
        if (advancedPopup.opened)
            advancedPopup.close()
        if (focusReturnTarget)
            focusReturnTarget.forceActiveFocus()
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiPopupHeader {
            iconName: "equalizer"
            title: qsTr("Equalizer")
            subtitle: qsTr("Shape the playback sound")
            badgeText: root.available
                ? root.bridgeValue("stateLabel", qsTr("Ready"))
                : qsTr("Unavailable")
            badgeTone: !root.available ? "warning"
                : root.bridgeValue("stateLabel", "") === "Error" ? "error"
                : root.bridgeValue("stateLabel", "") === "Applying" ? "active"
                : root.bridgeValue("stateLabel", "").indexOf("Effective") === 0
                    ? "success" : "neutral"

            trailingData: MichiSwitch {
                checked: root.bridgeValue("enabledDraft", true)
                enabled: root.controlsEnabled
                focusPolicy: Qt.StrongFocus
                Accessible.name: qsTr("Enable equalizer")
                onToggled: {
                    if (root.processingBridge)
                        root.processingBridge.set_bypass_requested(!checked)
                    root.commitDraft()
                }
            }
        }

        MichiText {
            visible: !root.available
            text: root.bridgeValue(
                "capabilityReason",
                qsTr("Audio processing is unavailable for the current output"))
            role: "secondary"
            color: MichiPalette.warning
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            MichiButton {
                text: qsTr("Calculated response")
                variant: "ghost"
                checkable: true
                checked: root.showResponse
                enabled: root.bridgeValue("responseAvailable", false)
                implicitHeight: MichiMetrics.controlSmall
                onClicked: root.showResponse = checked
            }
            Item { Layout.fillWidth: true }
            MichiText {
                visible: !root.bridgeValue("responseAvailable", false)
                text: qsTr("Select a track to calculate")
                role: "micro"
                color: MichiPalette.textMuted
            }
        }

        MichiEqResponsePlot {
            visible: root.showResponse
            Layout.fillWidth: true
            Layout.preferredHeight: 112
            points: root.bridgeValue("responseCurve", [])
            sampleRate: 0
        }

        Flickable {
            id: railScroll
            Layout.fillWidth: true
            Layout.preferredHeight: 194
            contentWidth: width
            contentHeight: railRow.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            RowLayout {
                id: railRow
                width: railScroll.width
                spacing: MichiSpacing.xxs

                Repeater {
                    id: railRepeater
                    model: root.bands
                    delegate: MichiEqSlider {
                        required property var modelData
                        required property int index
                        objectName: "eqBand_" + index
                        Layout.fillWidth: true
                        Layout.minimumWidth: 32
                        bandLabel: modelData.label
                        gainDb: modelData.gainDb
                        inactive: modelData.inactiveReason !== ""
                        inactiveReason: modelData.inactiveReason
                        enabled: root.controlsEnabled
                        onGainCommitted: gain => {
                            if (root.processingBridge)
                                root.processingBridge.set_draft_band(index, gain)
                            root.commitDraft()
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            MichiText {
                text: qsTr("Presets")
                role: "caption"
                color: MichiPalette.textSecondary
            }
            Repeater {
                model: root.presets
                delegate: MichiButton {
                    required property var modelData
                    text: modelData.displayName || modelData.label || modelData.id || ""
                    variant: "ghost"
                    implicitHeight: MichiMetrics.controlSmall
                    selected: root.bridgeValue("presetId", "") === modelData.id
                    enabled: root.controlsEnabled
                    onClicked: {
                        if (root.processingBridge)
                            root.processingBridge.select_preset(modelData.id)
                        root.commitDraft()
                    }
                }
            }
            Item { Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.md
            MichiText {
                text: qsTr("Preamp")
                role: "technical"
                technical: true
                color: MichiPalette.textSecondary
            }
            MichiSlider {
                id: preampSlider
                objectName: "preampSlider"
                Layout.fillWidth: true
                from: -24
                to: 24
                stepSize: 0.5
                value: root.bridgeValue("preampDb", 0)
                enabled: root.controlsEnabled
                accessibleName: qsTr("Preamp gain")
                onMoved: {
                    if (root.processingBridge)
                        root.processingBridge.set_draft_preamp(value)
                    // Keyboard changes have no release event; coalesce them.
                    if (!pressed)
                        preampCommitTimer.restart()
                }
                onPressedChanged: {
                    if (pressed)
                        return
                    preampCommitTimer.stop()
                    if (root.processingBridge)
                        root.processingBridge.set_draft_preamp(value)
                    root.commitDraft()
                }
                Timer {
                    id: preampCommitTimer
                    interval: 300
                    repeat: false
                    onTriggered: root.commitDraft()
                }
            }
            MichiText {
                text: root.bridgeValue("preampDb", 0).toFixed(1) + " dB"
                role: "technical"
                technical: true
                Layout.preferredWidth: 58
                horizontalAlignment: Text.AlignRight
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                text: root.bridgeValue("headroomLabel", qsTr("Headroom · not measured"))
                role: "caption"
                color: MichiPalette.textMuted
                Layout.fillWidth: true
            }
            MichiText {
                visible: root.bridgeValue("effectiveState", "unavailable") === "effective"
                text: qsTr("Effective · revision %1")
                    .arg(root.bridgeValue("committedRevision", 0))
                role: "micro"
                color: MichiPalette.success
            }
        }

        MichiText {
            visible: root.available && !root.bridgeValue("canApply", false)
            text: qsTr("Cannot apply now · no decoded PCM signal for this output")
            role: "caption"
            color: MichiPalette.warning
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        MichiText {
            visible: root.errorText !== ""
            text: root.errorText
            role: "caption"
            color: MichiPalette.error
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        MichiPopupFooter {
            MichiButton {
                text: qsTr("Reset Draft")
                variant: "ghost"
                enabled: root.controlsEnabled
                onClicked: {
                    if (root.processingBridge)
                        root.processingBridge.reset_draft()
                    root.commitDraft()
                }
            }
            MichiButton {
                text: qsTr("Advanced EQ")
                iconName: "chevron-right"
                enabled: root.available
                onClicked: {
                    root.advancedRequested()
                    // One focused surface at a time: the advanced editor
                    // replaces the quick EQ instead of stacking over it.
                    root.close()
                    advancedPopup.open()
                }
            }
        }
    }

    AdvancedEqualizerPopup {
        id: advancedPopup
        parent: Overlay.overlay
        processingBridge: root.processingBridge
        focusReturnTarget: root.focusReturnTarget
        x: parent ? Math.max(8, (parent.width - width) / 2) : 0
        y: parent ? Math.max(8, (parent.height - height) / 2) : 0
    }
}
