import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Zone Card"
    objectName: "audioZoneCard"
    focus: true
    id: root

    property string zoneName: ""
    property int receiverCount: 0
    property string zoneStatus: "idle"

    implicitHeight: 80

    GlassMaterial {
        anchors.fill: parent
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radius.md

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.zoneName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.receiverCount + " receptor(es)"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            StatusBadge {
                anchors.verticalCenter: parent.verticalCenter
                text: root.zoneStatus === "playing" ? "Reproduciendo" : qsTr("En espera")
                kind: root.zoneStatus === "playing" ? "active" : "disconnected"
            }
        }
    }
}
