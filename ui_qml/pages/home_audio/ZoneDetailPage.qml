import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string zoneId: ""
    property string zoneName: ""
    property int zoneVolume: 50
    property bool zoneMuted: false
    property string zoneSource: ""
    property string zoneStatus: "idle"
    property int zoneLatencyMs: 0
    property var zoneDevices: []

    signal backClicked()
    signal volumeChanged(string zoneId, float volume)
    signal muteToggled(string zoneId, bool muted)
    signal sourceChanged(string zoneId, string source)
    signal reconnectClicked(string zoneId)
    signal groupClicked(string zoneId)
    signal ungroupClicked(string zoneId)

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            MichiButton {
                text: "< Volver"
                variant: "ghost"
                onClicked: root.backClicked()
            }

            GlassMaterial {
                width: parent.width
                height: 200
                radius: MichiTheme.radiusMd
                variant: "elevated"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: root.zoneName
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Row { spacing: MichiTheme.spacing.sm
                        StatusBadge {
                            text: root.zoneStatus === "playing" ? "Reproduciendo" : "En espera"
                            kind: root.zoneStatus === "playing" ? "active" : "disconnected"
                        }
                        StatusBadge { text: root.zoneMuted ? "Silenciado" : "Activo"; kind: root.zoneMuted ? "warning" : "success" }
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        Text { text: "Origen:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        Text { text: root.zoneSource || "Ninguno"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                    }

                    Text { text: "Latencia: " + root.zoneLatencyMs + " ms"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; visible: root.zoneLatencyMs > 0 }
                }
            }

            LatencyControl {
                id: latencyCtrl
                width: parent.width
                currentLatencyMs: root.zoneLatencyMs
                onLatencyChanged: function(ms) {
                    root.zoneLatencyMs = ms
                }
            }

            MultiroomStatus {
                id: multiroomStatus
                width: parent.width
                zoneId: root.zoneId
                zoneDevices: root.zoneDevices
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton { text: "Reconectar"; variant: "primary"; onClicked: root.reconnectClicked(root.zoneId) }
                MichiButton { text: "Agrupar"; variant: "secondary"; onClicked: root.groupClicked(root.zoneId) }
                MichiButton { text: "Desagrupar"; variant: "ghost"; onClicked: root.ungroupClicked(root.zoneId) }
            }

            PlaybackTransferDialog {
                id: transferDialog
                width: parent.width
                visible: false
            }
        }
    }
}
