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
    readonly property var tabs: [
        {"id": "graphic", "label": qsTr("Graphic")},
        {"id": "parametric", "label": qsTr("Parametric")},
        {"id": "convolution", "label": qsTr("Convolution / FIR")},
        {"id": "signal", "label": qsTr("Signal / Resampling")},
        {"id": "profiles", "label": qsTr("Profiles")}
    ]
    readonly property var bands: processingBridge ? processingBridge.bands : []
    readonly property string effectiveState: processingBridge
        ? processingBridge.effectiveState : "unavailable"

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
    // Advanced EQ is centred in the scene, so the window overlay owns both
    // dimensions. Binding to the opener clipped the whole surface to 2 px.
    width: Math.max(680, Math.min(760, (Overlay.overlay
        ? Overlay.overlay.width : 800) - 32))
    height: Math.max(480, Math.min(640, (Overlay.overlay
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

    onOpened: tabBar.forceActiveFocus()
    onClosed: if (focusReturnTarget) focusReturnTarget.forceActiveFocus()

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiPopupHeader {
            iconName: "sliders"
            title: qsTr("Advanced Equalizer")
            subtitle: qsTr("Precision sound shaping")
            badgeText: root.effectiveState === "effective"
                ? qsTr("Applied · revision %1").arg(root.bridgeValue("committedRevision", 0))
                : root.effectiveState === "bypassed" ? qsTr("Bypassed")
                : qsTr("Unavailable")
            badgeTone: root.effectiveState === "effective" ? "success"
                : root.effectiveState === "bypassed" ? "neutral" : "warning"
        }

        RowLayout {
            id: tabBar
            Layout.fillWidth: true
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
            Item { Layout.fillWidth: true }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: Math.max(0, root.tabs.findIndex(function (tab) {
                return tab.id === root.activeTab
            }))

            // Graphic: 31 ISO bands are not wired to a proven runtime mapping.
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.md
                    MichiText {
                        text: qsTr("31-band graphic editor")
                        role: "section"
                    }
                    MichiText {
                        text: qsTr("This view stays unavailable until the 31 ISO bands are mapped to a proven backend graph. The ten-band quick EQ remains fully functional.")
                        role: "secondary"
                        color: MichiPalette.warning
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        Layout.preferredWidth: root.width - 2 * MichiSpacing.xl
                    }
                    GridLayout {
                        columns: 8
                        columnSpacing: MichiSpacing.sm
                        rowSpacing: MichiSpacing.sm
                        Layout.fillWidth: true
                        Repeater {
                            model: 31
                            delegate: Rectangle {
                                required property int index
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
                                radius: MichiRadius.sm
                                color: MichiPalette.smoke
                                border.width: 1
                                border.color: MichiSemanticColors.borderSubtle
                                MichiText {
                                    anchors.centerIn: parent
                                    text: qsTr("ISO %1").arg(index + 1)
                                    role: "micro"
                                    color: MichiPalette.textDisabled
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
                        text: qsTr("The quick EQ is stored as ten PEAK biquads. Editing filter type or Q requires a backend capability that is not wired yet.")
                        role: "secondary"
                        color: MichiPalette.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Repeater {
                        model: root.bands
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            spacing: MichiSpacing.md
                            MichiText {
                                text: modelData.label + " Hz"
                                role: "technical"
                                technical: true
                                Layout.preferredWidth: 90
                            }
                            MichiText {
                                text: qsTr("PEAK")
                                role: "caption"
                                color: MichiPalette.textSecondary
                                Layout.preferredWidth: 70
                            }
                            MichiText {
                                text: (modelData.gainDb >= 0 ? "+" : "")
                                    + modelData.gainDb.toFixed(1) + " dB"
                                role: "technical"
                                technical: true
                                Layout.fillWidth: true
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
                            MichiText {
                                text: modelData.displayName || modelData.label || modelData.id || ""
                                role: "body"
                                Layout.fillWidth: true
                            }
                            MichiStatusChip {
                                text: root.bridgeValue("presetId", "") === modelData.id
                                    ? qsTr("Active") : qsTr("Available")
                                tone: root.bridgeValue("presetId", "") === modelData.id
                                    ? "active" : "neutral"
                                dotVisible: false
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
            MichiButton {
                text: qsTr("Discard")
                variant: "ghost"
                onClicked: {
                    if (root.processingBridge)
                        root.processingBridge.discard_draft()
                    root.close()
                }
            }
            MichiButton {
                text: qsTr("Validate")
                variant: "ghost"
                onClicked: {
                    if (root.processingBridge)
                        root.processingBridge.validate_draft()
                }
            }
            MichiButton {
                text: qsTr("Apply")
                enabled: root.processingBridge ? root.processingBridge.canApply : false
                onClicked: {
                    if (root.processingBridge)
                        root.processingBridge.apply_draft_async()
                }
            }
        }
    }
}
