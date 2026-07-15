import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    objectName: "zoneDetailPage"

    property string zoneId: ""
    property string zoneName: ""
    property int zoneVolume: 50
    property bool zoneMuted: false
    property string zoneSource: ""
    property string zoneStatus: "idle"
    property int zoneLatencyMs: 0
    property var zoneDevices: []

    signal backClicked()
    signal zoneDetailVolumeChanged(string zoneId, real volume)
    signal muteToggled(string zoneId, bool muted)
    signal sourceChanged(string zoneId, string source)
    signal reconnectClicked(string zoneId)
    signal groupClicked(string zoneId)
    signal ungroupClicked(string zoneId)

    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle de zona: " + root.zoneName

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true
        objectName: "zoneDetail.focusScope"

        Keys.onEscapePressed: root.backClicked()

        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "zoneDetail.flickable"

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                MichiButton {
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "zoneDetail.backButton"
                    Accessible.name: "Volver a Home Audio"
                    KeyNavigation.tab: zoneHeader
                }

                GlassMaterial {
                    id: zoneHeader
                    width: parent.width
                    height: 340
                    radius: MichiTheme.radiusMd
                    variant: "elevated"
                    objectName: "zoneDetail.header"

                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: root.zoneName
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.pageTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            objectName: "zoneDetail.name"
                            Accessible.role: Accessible.Heading
                            Accessible.name: root.zoneName
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            objectName: "zoneDetail.statusRow"
                            StatusBadge {
                                text: root.zoneStatus === "playing" ? "Reproduciendo" : "En espera"
                                kind: root.zoneStatus === "playing" ? "active" : "disconnected"
                                Accessible.name: "Estado: " + text
                            }
                            StatusBadge {
                                text: root.zoneMuted ? "Silenciado" : "Activo"
                                kind: root.zoneMuted ? "warning" : "success"
                                Accessible.name: "Sonido: " + text
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.xs
                            Text { text: "Origen:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.zoneSource || "Ninguno"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Text {
                            text: "Latencia: " + root.zoneLatencyMs + " ms"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            visible: root.zoneLatencyMs > 0
                        }

                        SectionHeader { text: "Volumen"; width: parent.width }

                        Row {
                            spacing: MichiTheme.spacing.md
                            width: parent.width
                            objectName: "zoneDetail.volumeRow"

                            MichiSlider {
                                id: volumeSlider
                                width: parent.width - 100
                                from: 0; to: 100
                                value: root.zoneVolume
                                stepSize: 1
                                anchors.verticalCenter: parent.verticalCenter
                                accessibleName: "Volumen de zona"
                                onMoved: root.zoneDetailVolumeChanged(root.zoneId, value)
                                KeyNavigation.tab: muteButton
                            }

                            Text {
                                text: Math.round(volumeSlider.value) + "%"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        MichiButton {
                            id: muteButton
                            text: root.zoneMuted ? "Activar sonido" : "Silenciar"
                            variant: root.zoneMuted ? "secondary" : "ghost"
                            onClicked: root.muteToggled(root.zoneId, !root.zoneMuted)
                            objectName: "zoneDetail.muteButton"
                            Accessible.name: root.zoneMuted ? "Activar sonido" : "Silenciar zona"
                            KeyNavigation.tab: reconnectBtn
                        }
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
                    objectName: "zoneDetail.actions"

                    MichiButton {
                        id: reconnectBtn
                        text: "Reconectar"; variant: "primary"
                        onClicked: root.reconnectClicked(root.zoneId)
                        objectName: "zoneDetail.reconnectButton"
                        Accessible.name: "Reconectar zona"
                        KeyNavigation.tab: groupBtn
                    }
                    MichiButton {
                        id: groupBtn
                        text: "Agrupar"; variant: "secondary"
                        onClicked: root.groupClicked(root.zoneId)
                        objectName: "zoneDetail.groupButton"
                        Accessible.name: "Agrupar zona"
                        KeyNavigation.tab: ungroupBtn
                    }
                    MichiButton {
                        id: ungroupBtn
                        text: "Desagrupar"; variant: "ghost"
                        onClicked: root.ungroupClicked(root.zoneId)
                        objectName: "zoneDetail.ungroupButton"
                        Accessible.name: "Desagrupar zona"
                        KeyNavigation.tab: backButton
                    }
                }

                PlaybackTransferDialog {
                    id: transferDialog
                    width: parent.width
                    visible: false
                }
            }
        }
    }
}
