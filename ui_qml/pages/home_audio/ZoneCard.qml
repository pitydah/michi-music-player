import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Zone Card"
    objectName: "zoneCard"
    focus: true
    id: root

    property string zoneName: ""
    property int deviceCount: 0
    property string zoneStatus: "idle"
    property bool isMuted: false
    property int volume: 50
    property bool hasLatency: false

    signal zoneCardClicked()
    signal zoneCardVolumeChanged(int volume)
    signal zoneMuteToggled()

    implicitHeight: 100

    GlassMaterial {
        anchors.fill: parent
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radiusMd

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.zoneCardClicked()
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.md

                Column {
                    width: parent.width - 160
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: root.zoneName
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                        width: parent.width
                    }

                    Text {
                        text: root.deviceCount + " dispositivo(s)"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.xs
                    anchors.verticalCenter: parent.verticalCenter

                    StatusBadge {
                        text: root.zoneStatus === "playing" ? "Reproduciendo" : "En espera"
                        kind: root.zoneStatus === "playing" ? "active" : "disconnected"
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: root.isMuted ? "Activar sonido" : "Silenciar"
                    variant: root.isMuted ? "secondary" : "ghost"
                    onClicked: root.zoneMuteToggled()
                }

                Text {
                    text: "Vol: " + root.volume + "%"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
