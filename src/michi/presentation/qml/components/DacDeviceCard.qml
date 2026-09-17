import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root
    property var device: ({})
    property var signalPath: []
    property var reasonCodes: []
    signal selectionRequested(string stableDeviceId)

    implicitHeight: cardContent.implicitHeight

    ColumnLayout {
        id: cardContent
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: MichiSpacing.xs

        Button {
            id: selectionButton
            objectName: "audioOutputDeviceCard_" + (root.device.stableDeviceId || "shared")
            Layout.fillWidth: true
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            enabled: root.device.canSelect
            padding: MichiSpacing.md
            onClicked: root.selectionRequested(root.device.stableDeviceId || "")
            Keys.onReturnPressed: selectionButton.clicked()
            Keys.onEnterPressed: selectionButton.clicked()
            Accessible.name: (root.device.displayName || qsTr("Audio Output"))
                + " — " + (root.device.statusLabel || "")
            Accessible.description: qsTr("%1 path. %2. %3")
                .arg(root.device.transportLabel || qsTr("Shared"))
                .arg(root.device.volumeLabel || qsTr("Volume follows the active output"))
                .arg(root.device.signalTruthLabel || qsTr("Not verified"))

            contentItem: ColumnLayout {
                spacing: MichiSpacing.sm
                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiIcon {
                        Layout.preferredWidth: 22
                        Layout.preferredHeight: 22
                        name: root.device.isShared ? "audio-output" : "audio-engine"
                        iconColor: root.device.active
                            ? MichiPalette.auroraCyan : MichiPalette.textSecondary
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: root.device.displayName || qsTr("Audio Output")
                        role: "heading"
                        elide: Text.ElideRight
                    }
                    MichiText {
                        text: root.device.connectionLabel || qsTr("Unavailable")
                        role: "secondary"
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.xs
                    MichiStatusChip {
                        text: root.device.statusLabel || qsTr("Available")
                        tone: root.device.active ? "active"
                            : root.device.available ? "neutral" : "warning"
                    }
                    MichiStatusChip {
                        text: root.device.transportLabel || qsTr("Shared")
                        tone: root.device.transportMode === "direct" ? "active" : "neutral"
                    }
                    MichiStatusChip {
                        text: root.device.signalTruthLabel || qsTr("Not verified")
                        tone: root.device.signalTruthLabel === "Output mismatch"
                            ? "error" : "neutral"
                    }
                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    visible: root.device.active
                    Layout.fillWidth: true
                    MichiText {
                        Layout.fillWidth: true
                        text: qsTr("Signal %1 → %2")
                            .arg(root.device.sourceRateLabel || "—")
                            .arg(root.device.deviceRateLabel || "—")
                        role: "technical"
                        technical: true
                    }
                    MichiText {
                        text: root.device.volumeLabel || qsTr("Volume unavailable")
                        role: "secondary"
                    }
                }
            }

            background: Rectangle {
                radius: MichiRadius.md
                color: selectionButton.pressed
                    ? MichiSemanticColors.surfacePressed
                    : selectionButton.hovered
                        ? MichiSemanticColors.surfaceHover
                        : MichiSemanticColors.contentSurface
                border.width: selectionButton.visualFocus || root.device.selected ? 1 : 0
                border.color: selectionButton.visualFocus
                    ? MichiSemanticColors.focusRing
                    : root.device.active
                        ? MichiSemanticColors.auroraCyanBorder
                        : MichiSemanticColors.borderStrong
            }
        }

        DacDiagnosticsDisclosure {
            visible: !root.device.isShared
            Layout.fillWidth: true
            device: root.device
            signalPath: root.signalPath
            reasonCodes: root.reasonCodes
            signalTruthLabel: root.device.signalTruthLabel || qsTr("Not verified")
        }
    }
}
