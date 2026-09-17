pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "../components"
import "../primitives"
import "../theme"

Item {
    id: root
    property var devices: []
    property var profiles: []
    property string selectedDeviceId: ""
    property string activeDeviceId: ""
    property string outputState: "idle"
    property string volumeLabel: qsTr("Volume unavailable")
    property string signalTruthLabel: qsTr("Not verified")
    property var signalTruthReasonCodes: []
    property var signalPath: []
    property string lastFailureTitle: ""
    property string lastFailureDisplay: ""
    property bool canUseDirect: false

    signal deviceSelectionRequested(string stableDeviceId)
    signal sharedSelectionRequested()

    implicitHeight: panelContent.implicitHeight + MichiSpacing.lg * 2

    MichiGlassSurface {
        id: outputPanel
        objectName: "audioOutputSettingsPanel"
        anchors.fill: parent

        ColumnLayout {
            id: panelContent
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: MichiSpacing.md

            MichiText {
                text: qsTr("Audio Output / DAC")
                role: "heading"
                Accessible.role: Accessible.Heading
            }
            MichiText {
                Layout.fillWidth: true
                text: qsTr("Choose where Michi sends audio. Selection and active playback are shown separately.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }

            Rectangle {
                visible: root.lastFailureTitle !== ""
                Layout.fillWidth: true
                implicitHeight: failureContent.implicitHeight + MichiSpacing.md * 2
                radius: MichiRadius.md
                color: MichiSemanticColors.contentSurface
                border.width: 1
                border.color: MichiSemanticColors.statusBorder(MichiPalette.error)

                ColumnLayout {
                    id: failureContent
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.md
                    MichiText {
                        text: root.lastFailureTitle
                        role: "primary"
                        font.weight: Font.DemiBold
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: root.lastFailureDisplay
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                }
            }

            MichiText {
                visible: !root.canUseDirect
                    && root.devices.some(function(item) { return !item.isShared })
                Layout.fillWidth: true
                text: qsTr("Direct requires GStreamer. Select it explicitly in Audio Engine settings.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }

            ColumnLayout {
                id: deviceCards
                objectName: "audioOutputDeviceCards"
                Layout.fillWidth: true
                spacing: MichiSpacing.md

                Repeater {
                    objectName: "audioOutputDeviceRepeater"
                    model: root.devices
                    delegate: DacDeviceCard {
                        id: deviceCard
                        required property var modelData
                        Layout.fillWidth: true
                        device: deviceCard.modelData
                        signalPath: deviceCard.modelData.active ? root.signalPath : []
                        reasonCodes: deviceCard.modelData.active
                            ? root.signalTruthReasonCodes : []
                        onSelectionRequested: stableDeviceId => {
                            if (stableDeviceId === "")
                                root.sharedSelectionRequested()
                            else
                                root.deviceSelectionRequested(stableDeviceId)
                        }
                    }
                }
            }

            ColumnLayout {
                visible: root.devices.length === 1 && root.devices[0].isShared
                Layout.fillWidth: true
                spacing: MichiSpacing.xs
                MichiText {
                    text: qsTr("No DAC detected")
                    role: "primary"
                }
                MichiText {
                    Layout.fillWidth: true
                    text: qsTr("Connect a USB DAC or use Shared system output.")
                    role: "secondary"
                    wrapMode: Text.WordWrap
                }
            }

            MichiText {
                Layout.fillWidth: true
                text: qsTr("Signal Truth is software runtime evidence. It is not a physical or bit-perfect certification.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
        }
    }
}
