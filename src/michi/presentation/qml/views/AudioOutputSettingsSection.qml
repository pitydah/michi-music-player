pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "../components"
import "../controls" as Controls
import "../primitives"
import "../theme"

Item {
    id: root
    property var devices: []
    property var profiles: []
    property string selectedDeviceId: ""
    property string selectedProfileId: ""
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
    signal profileSelectionRequested(string profileId)

    function selectedProfileIndex() {
        for (var i = 0; i < root.profiles.length; ++i) {
            if (root.profiles[i].profileId === root.selectedProfileId)
                return i
        }
        return -1
    }

    function syncProfileSelection() {
        profileSelector.currentIndex = root.selectedProfileIndex()
    }

    onProfilesChanged: Qt.callLater(root.syncProfileSelection)
    onSelectedProfileIdChanged: Qt.callLater(root.syncProfileSelection)
    Component.onCompleted: root.syncProfileSelection()

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

            RowLayout {
                objectName: "audioOutputProfileRow"
                Layout.fillWidth: true
                spacing: MichiSpacing.md

                ColumnLayout {
                    objectName: "audioOutputProfileCopy"
                    Layout.fillWidth: true
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: qsTr("Output profile")
                        role: "primary"
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: root.profiles.length > 0
                            ? qsTr("Choose a saved path for an available device.")
                            : qsTr("No saved output profiles are available.")
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                }

                Controls.MichiComboBox {
                    id: profileSelector
                    objectName: "audioOutputProfileSelector"
                    Layout.minimumWidth: 260
                    Layout.preferredWidth: 360
                    model: root.profiles
                    textRole: "displayName"
                    enabledRole: "actionEnabled"
                    enabled: root.profiles.length > 0
                    accessibleName: qsTr("Output profile")
                    onActivated: index => {
                        var profile = root.profiles[index]
                        if (profile && profile.actionEnabled)
                            root.profileSelectionRequested(profile.profileId)
                        Qt.callLater(root.syncProfileSelection)
                    }
                }
            }
            MichiText {
                Layout.fillWidth: true
                text: qsTr("Choose where Michi sends audio. Selection and active playback are shown separately.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }

            Rectangle {
                objectName: "audioOutputFailureBanner"
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
