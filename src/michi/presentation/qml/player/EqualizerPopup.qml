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
    signal advancedRequested()

    readonly property bool available: processingBridge
        ? processingBridge.available : false
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

    padding: MichiSpacing.lg
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: Math.min(440, parent ? parent.width - 24 : 440)
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
    }

    onOpened: {
        if (advancedPopup.opened)
            advancedPopup.close()
        for (var i = 0; i < railRepeater.count; ++i) {
            var rail = railRepeater.itemAt(i)
            if (rail && rail.enabled) {
                rail.forceActiveFocus()
                break
            }
        }
    }
    onClosed: {
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
                ? (root.bridgeValue("enabledDraft", true) ? qsTr("ON") : qsTr("OFF"))
                : qsTr("Unavailable")
            badgeTone: root.available
                ? (root.bridgeValue("enabledDraft", true) ? "active" : "neutral")
                : "warning"

            trailingData: Switch {
                checked: root.bridgeValue("enabledDraft", true)
                enabled: root.available
                focusPolicy: Qt.StrongFocus
                Accessible.name: qsTr("Enable equalizer")
                onToggled: {
                    if (root.processingBridge)
                        root.processingBridge.set_bypass_requested(!checked)
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
                        Layout.fillWidth: true
                        Layout.minimumWidth: 32
                        bandLabel: modelData.label
                        gainDb: modelData.gainDb
                        inactive: modelData.inactiveReason !== ""
                        inactiveReason: modelData.inactiveReason
                        enabled: root.available
                        onGainCommitted: gain => {
                            if (root.processingBridge)
                                root.processingBridge.set_draft_band(index, gain)
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
                    enabled: root.available
                    onClicked: {
                        if (root.processingBridge)
                            root.processingBridge.select_preset(modelData.id)
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
                Layout.fillWidth: true
                from: -24
                to: 24
                stepSize: 0.5
                value: root.bridgeValue("preampDb", 0)
                enabled: root.available
                accessibleName: qsTr("Preamp gain")
                onMoved: {
                    if (root.processingBridge)
                        root.processingBridge.set_draft_preamp(value)
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
            visible: root.errorText !== ""
            text: root.errorText
            role: "caption"
            color: MichiPalette.error
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        MichiPopupFooter {
            MichiButton {
                text: qsTr("Reset")
                variant: "ghost"
                enabled: root.available
                onClicked: {
                    if (root.processingBridge)
                        root.processingBridge.reset_draft()
                }
            }
            MichiButton {
                text: qsTr("Advanced EQ")
                iconName: "chevron-right"
                enabled: root.available
                onClicked: {
                    root.advancedRequested()
                    advancedPopup.open()
                }
            }
        }
    }

    AdvancedEqualizerPopup {
        id: advancedPopup
        parent: root.parent
        processingBridge: root.processingBridge
        x: parent ? Math.max(8, (parent.width - width) / 2) : 0
        y: parent ? Math.max(8, (parent.height - height) / 2) : 0
    }
}
