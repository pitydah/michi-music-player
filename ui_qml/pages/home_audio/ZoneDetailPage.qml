import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Zone Detail"
    objectName: "zoneDetailPage"
    id: root
    focus: true

    property string zoneId: ""
    property string zoneName: ""
    property int zoneVolume: 50
    property bool zoneMuted: false
    property string zoneSource: ""
    property string zoneStatus: "idle"
    property int zoneLatencyMs: 0
    property var zoneDevices: []
    property bool zoneOnline: true
    property string zoneState: "ready"

    signal backClicked()
    signal zoneDetailVolumeChanged(string zoneId, real volume)
    signal muteToggled(string zoneId, bool muted)
    signal sourceChanged(string zoneId, string source)
    signal reconnectClicked(string zoneId)
    signal groupClicked(string zoneId)
    signal ungroupClicked(string zoneId)
    signal renameRequested(string zoneId, string newName)
    signal deleteRequested(string zoneId)



    AsyncStateView {
        id: asyncView
        anchors.fill: parent
        state: root.zoneState === "loading" ? AsyncStateView.LOADING
             : root.zoneState === "error" ? AsyncStateView.ERROR
             : root.zoneState === "unavailable" ? AsyncStateView.UNAVAILABLE
             : root.zoneState === "degraded" ? AsyncStateView.DEGRADED
             : AsyncStateView.READY
        title: root.zoneState === "error" ? "Error en zona" : root.zoneState === "degraded" ? "Funcionamiento degradado" : ""
        message: root.zoneOnline ? "" : "La zona no está disponible en este momento"
        retryAvailable: root.zoneState === "error" || !root.zoneOnline
        onRetryRequested: root.reconnectClicked(root.zoneId)

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                MichiButton {
                    Accessible.role: Accessible.Button

                    id: backBtn
                    activeFocusOnTab: true

                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    KeyNavigation.tab: zoneNameText
                    Keys.onReturnPressed: root.backClicked()
                    Keys.onSpacePressed: root.backClicked()
                }

                Text {
                    id: zoneNameText
                    text: root.zoneName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    KeyNavigation.tab: statusBar
                    KeyNavigation.backtab: backBtn
                }

                Row {
                    id: statusBar
                    spacing: MichiTheme.spacing.sm

                    StatusBadge {
                        text: root.zoneOnline ? "En línea" : "Desconectado"
                        kind: root.zoneOnline ? "success" : "error"
                    }

                    StatusBadge {
                        text: {
                            switch (root.zoneStatus) {
                                case "playing": return "Reproduciendo"
                                case "paused": return "En pausa"
                                default: return "En espera"
                            }
                        }
                        kind: root.zoneStatus === "playing" ? "active" : "disconnected"
                    }

                    StatusBadge {
                        text: root.zoneMuted ? "Silenciado" : "Activo"
                        kind: root.zoneMuted ? "warning" : "success"
                    }
                }

                GlassMaterial {
                    id: volumeCard
                    width: parent.width
                    height: 80
                    radius: MichiTheme.radius.md
                    variant: "base"

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Volumen"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            width: 80
                        }
                            Accessible.role: Accessible.Slider

                            activeFocusOnTab: true


                        MichiSlider {
                            id: volumeSlider
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 200
                            from: 0
                            to: 100
                            value: root.zoneVolume
                            stepSize: 1
                            accessibleName: "Volumen de " + root.zoneName
                            accessibleDescription: root.zoneVolume + "%"
                            onMoved: {
                                root.zoneVolume = value
                                root.zoneDetailVolumeChanged(root.zoneId, value / 100.0)
                            }
                            enabled: !root.zoneMuted
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.zoneVolume + "%"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: 40
                            Accessible.role: Accessible.Button

                            activeFocusOnTab: true

                            horizontalAlignment: Text.AlignRight
                        }

                        MichiButton {
                            id: muteBtn
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.zoneMuted ? "Activar sonido" : "Silenciar"
                            variant: root.zoneMuted ? "secondary" : "ghost"
                            onClicked: {
                                root.zoneMuted = !root.zoneMuted
                                root.muteToggled(root.zoneId, root.zoneMuted)
                            }
                        }
                    }
                }

                GlassMaterial {
                    id: infoCard
                    width: parent.width
                    height: infoColumn.height + MichiTheme.spacing.xl * 2
                    radius: MichiTheme.radius.md
                    variant: "base"

                    Column {
                        id: infoColumn
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Información de la zona"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text { text: "ID: " + root.zoneId; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.zoneId !== "" }
                        Text { text: "Origen: " + (root.zoneSource || "Ninguno"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        Text { text: "Latencia: " + root.zoneLatencyMs + " ms"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.zoneLatencyMs > 0 }
                        Text { text: root.zoneDevices.length + " dispositivo(s) en la zona"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }

                        Repeater {
                            model: root.zoneDevices
                            Row {
                                spacing: MichiTheme.spacing.sm
                                width: parent.width
                                Text {
                                    text: modelData.name || "Dispositivo"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    width: parent.width - 100
                                    elide: Text.ElideRight
                                }
                                StatusBadge {
                                    text: modelData.connected ? "Conectado" : "Desconectado"
                                    kind: modelData.connected ? "success" : "disconnected"
                                }
                            }
                        }
                    }
                }
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true


                Row {
                    id: actionRow
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        id: reconnBtn
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                        text: "Reconectar"
                        variant: "primary"
                        onClicked: root.reconnectClicked(root.zoneId)
                        KeyNavigation.tab: groupBtn
                        KeyNavigation.backtab: muteBtn
                    }

                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                    MichiButton {
                        id: groupBtn
                        text: "Agrupar"
                        variant: "secondary"
                        onClicked: root.groupClicked(root.zoneId)
                        KeyNavigation.tab: ungroupBtn
                        KeyNavigation.backtab: reconnBtn
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                    }

                    MichiButton {
                        id: ungroupBtn
                        text: "Desagrupar"
                        variant: "ghost"
                        onClicked: root.ungroupClicked(root.zoneId)
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                        KeyNavigation.tab: renameBtn
                        KeyNavigation.backtab: groupBtn
                    }

                    MichiButton {
                        id: renameBtn
                        text: "Renombrar"
                        variant: "ghost"
                        onClicked: root.renameRequested(root.zoneId, "")
                        KeyNavigation.tab: deleteBtn
                        KeyNavigation.backtab: ungroupBtn
                    }

                    MichiButton {
                        id: deleteBtn
                        text: "Eliminar zona"
                        variant: "danger"
                        onClicked: root.deleteRequested(root.zoneId)
                        Accessible.description: "Elimina permanentemente la zona"
                        KeyNavigation.backtab: renameBtn
                    }
                }
            }
        }

        degradedOverlay: Rectangle {
            color: MichiTheme.colors.badgeWarningBg
            radius: MichiTheme.radius.md
            anchors.fill: parent
            visible: true

            Text {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: MichiTheme.spacing.sm
                text: "Funcionamiento degradado"
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.captionSize
                font.weight: MichiTheme.typography.weightMedium
            }
        }
    }
}
