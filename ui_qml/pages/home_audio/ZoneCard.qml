import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    objectName: "zoneCard"

    property string zoneName: ""
    property int deviceCount: 0
    property string zoneStatus: "idle"
    property bool isMuted: false
    property int volume: 50
    property bool hasLatency: false
    property bool online: true

    signal zoneCardClicked()
    signal zoneCardVolumeChanged(int volume)
    signal zoneMuteToggled()

    implicitHeight: 140

    Accessible.role: Accessible.Panel
    Accessible.name: "Zona: " + root.zoneName

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
                        Accessible.name: root.zoneName
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

                    StatusBadge {
                        text: root.online ? "En línea" : "Sin conexión"
                        kind: root.online ? "success" : "disconnected"
                        visible: true
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                objectName: "zoneCard.volumeRow"

                MichiSlider {
                    id: volumeSlider
                    width: parent.width - 140
                    from: 0; to: 100
                    value: root.volume
                    stepSize: 1
                    anchors.verticalCenter: parent.verticalCenter
                    accessibleName: "Volumen de " + root.zoneName
                    onMoved: root.zoneCardVolumeChanged(value)
                }

                Text {
                    text: "Vol: " + Math.round(volumeSlider.value) + "%"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                }

                MichiButton {
                    text: root.isMuted ? "🔇" : "🔊"
                    variant: root.isMuted ? "secondary" : "ghost"
                    implicitWidth: 36; implicitHeight: 36
                    onClicked: root.zoneMuteToggled()
                    objectName: "zoneCard.muteButton"
                    Accessible.name: root.isMuted ? "Activar sonido" : "Silenciar"
                }
            }
        }
    }
}
