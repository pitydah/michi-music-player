import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Controls
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    objectName: "homeAudio.zoneDetailPage"

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

    objectName: "zoneDetailPage"


    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle de zona: " + root.zoneName

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
            objectName: "zoneDetailFlickable"

    objectName: "zoneDetailPage"

    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle de zona: " + root.zoneName

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
            objectName: "zoneDetailFlickable"

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                MichiButton {
                    id: backBtn
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "zoneDetailBackButton"
                    Accessible.name: "Volver a Home Audio"
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
                    Accessible.name: "Zona: " + root.zoneName
                    objectName: "zoneDetailName"
                    KeyNavigation.tab: statusBar
                    KeyNavigation.backtab: backBtn
                }

                Row {
                    id: statusBar
                    spacing: MichiTheme.spacing.sm
                    objectName: "zoneDetailStatusBar"

                    StatusBadge {
                        text: root.zoneOnline ? "En línea" : "Desconectado"
                        kind: root.zoneOnline ? "success" : "error"
                        Accessible.name: "Estado de conexión: " + text
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
                        Accessible.name: "Estado de reproducción: " + text
                    }
                }

                    StatusBadge {
                        text: root.zoneMuted ? "Silenciado" : "Activo"
                        kind: root.zoneMuted ? "warning" : "success"
                        Accessible.name: root.zoneMuted ? "Zona silenciada" : "Zona activa"
                    }
                }

                GlassMaterial {
                    id: volumeCard
                    width: parent.width
                    height: 80
                    radius: MichiTheme.radiusMd
                    variant: "base"
                    objectName: "zoneDetailVolumeCard"
                    Accessible.name: "Control de volumen"

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
                            objectName: "zoneDetailVolumeSlider"
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.zoneVolume + "%"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: 40
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
                            objectName: "zoneDetailMuteButton"
                            Accessible.name: root.zoneMuted ? "Activar sonido de " + root.zoneName : "Silenciar " + root.zoneName
                        }
                    id: backBtn
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "zoneDetailBackButton"
                    Accessible.name: "Volver a Home Audio"
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
                    Accessible.name: "Zona: " + root.zoneName
                    objectName: "zoneDetailName"
                    KeyNavigation.tab: statusBar
                    KeyNavigation.backtab: backBtn
                }

                Row {
                    id: statusBar
                    spacing: MichiTheme.spacing.sm
                    objectName: "zoneDetailStatusBar"

                    StatusBadge {
                        text: root.zoneOnline ? "En línea" : "Desconectado"
                        kind: root.zoneOnline ? "success" : "error"
                        Accessible.name: "Estado de conexión: " + text
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
                        Accessible.name: "Estado de reproducción: " + text
                    }
                }

                GlassMaterial {
                    id: infoCard
                LatencyControl {
                    id: latencyCtrl
                    width: parent.width
                    height: infoColumn.height + MichiTheme.spacing.xl * 2
                    radius: MichiTheme.radiusMd
                    variant: "base"
                    objectName: "zoneDetailInfoCard"
                    Accessible.name: "Información de la zona"

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
                    id: backBtn
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "zoneDetailBackButton"
                    Accessible.name: "Volver a Home Audio"
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
                    Accessible.name: "Zona: " + root.zoneName
                    objectName: "zoneDetailName"
                    KeyNavigation.tab: statusBar
                    KeyNavigation.backtab: backBtn
                }

                Row {
                    id: statusBar
                    spacing: MichiTheme.spacing.sm
                    objectName: "zoneDetailStatusBar"

                    StatusBadge {
                        text: root.zoneOnline ? "En línea" : "Desconectado"
                        kind: root.zoneOnline ? "success" : "error"
                        Accessible.name: "Estado de conexión: " + text
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
                        Accessible.name: "Estado de reproducción: " + text
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
                    id: actionRow
                    spacing: MichiTheme.spacing.sm
                    objectName: "zoneDetailActions"

                    MichiButton {
                        id: reconnBtn
                        text: "Reconectar"
                        variant: "primary"
                        onClicked: root.reconnectClicked(root.zoneId)
                        objectName: "zoneDetailReconnectButton"
                        Accessible.name: "Reconectar zona " + root.zoneName
                        KeyNavigation.tab: groupBtn
                        KeyNavigation.backtab: muteBtn
                    }

                    MichiButton {
                        id: groupBtn
                        text: "Agrupar"
                        variant: "secondary"
                        onClicked: root.groupClicked(root.zoneId)
                        objectName: "zoneDetailGroupButton"
                        Accessible.name: "Agrupar zona " + root.zoneName + " con otras zonas"
                        KeyNavigation.tab: ungroupBtn
                        KeyNavigation.backtab: reconnBtn
                    }

                    MichiButton {
                        id: ungroupBtn
                        text: "Desagrupar"
                        variant: "ghost"
                        onClicked: root.ungroupClicked(root.zoneId)
                        objectName: "zoneDetailUngroupButton"
                        Accessible.name: "Desagrupar zona " + root.zoneName
                        KeyNavigation.tab: renameBtn
                        KeyNavigation.backtab: groupBtn
                    }

                    MichiButton {
                        id: renameBtn
                        text: "Renombrar"
                        variant: "ghost"
                        onClicked: root.renameRequested(root.zoneId, "")
                        objectName: "zoneDetailRenameButton"
                        Accessible.name: "Renombrar zona " + root.zoneName
                        KeyNavigation.tab: deleteBtn
                        KeyNavigation.backtab: ungroupBtn
                    }

                    MichiButton {
                        id: deleteBtn
                        text: "Eliminar zona"
                        variant: "danger"
                        onClicked: root.deleteRequested(root.zoneId)
                        objectName: "zoneDetailDeleteButton"
                        Accessible.name: "Eliminar zona " + root.zoneName + ". Esta acción no se puede deshacer."
                        Accessible.description: "Elimina permanentemente la zona"
                        KeyNavigation.backtab: renameBtn
                    }
                }
            }
        }

                PlaybackTransferDialog {
                    id: transferDialog
                    width: parent.width
                    visible: false
                }
                    StatusBadge {
                        text: root.zoneMuted ? "Silenciado" : "Activo"
                        kind: root.zoneMuted ? "warning" : "success"
                        Accessible.name: root.zoneMuted ? "Zona silenciada" : "Zona activa"
                    }
                }

                GlassMaterial {
                    id: volumeCard
                    width: parent.width
                    height: 80
                    radius: MichiTheme.radiusMd
                    variant: "base"
                    objectName: "zoneDetailVolumeCard"
                    Accessible.name: "Control de volumen"

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
                            objectName: "zoneDetailVolumeSlider"
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.zoneVolume + "%"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: 40
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
                            objectName: "zoneDetailMuteButton"
                            Accessible.name: root.zoneMuted ? "Activar sonido de " + root.zoneName : "Silenciar " + root.zoneName
                        }
                    }
                }

                GlassMaterial {
                    id: infoCard
                    width: parent.width
                    height: infoColumn.height + MichiTheme.spacing.xl * 2
                    radius: MichiTheme.radiusMd
                    variant: "base"
                    objectName: "zoneDetailInfoCard"
                    Accessible.name: "Información de la zona"

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

                Row {
                    id: actionRow
                    spacing: MichiTheme.spacing.sm
                    objectName: "zoneDetailActions"

                    MichiButton {
                        id: reconnBtn
                        text: "Reconectar"
                        variant: "primary"
                        onClicked: root.reconnectClicked(root.zoneId)
                        objectName: "zoneDetailReconnectButton"
                        Accessible.name: "Reconectar zona " + root.zoneName
                        KeyNavigation.tab: groupBtn
                        KeyNavigation.backtab: muteBtn
                    }

                    MichiButton {
                        id: groupBtn
                        text: "Agrupar"
                        variant: "secondary"
                        onClicked: root.groupClicked(root.zoneId)
                        objectName: "zoneDetailGroupButton"
                        Accessible.name: "Agrupar zona " + root.zoneName + " con otras zonas"
                        KeyNavigation.tab: ungroupBtn
                        KeyNavigation.backtab: reconnBtn
                    }

                    MichiButton {
                        id: ungroupBtn
                        text: "Desagrupar"
                        variant: "ghost"
                        onClicked: root.ungroupClicked(root.zoneId)
                        objectName: "zoneDetailUngroupButton"
                        Accessible.name: "Desagrupar zona " + root.zoneName
                        KeyNavigation.tab: renameBtn
                        KeyNavigation.backtab: groupBtn
                    }

                    MichiButton {
                        id: renameBtn
                        text: "Renombrar"
                        variant: "ghost"
                        onClicked: root.renameRequested(root.zoneId, "")
                        objectName: "zoneDetailRenameButton"
                        Accessible.name: "Renombrar zona " + root.zoneName
                        KeyNavigation.tab: deleteBtn
                        KeyNavigation.backtab: ungroupBtn
                    }

                    MichiButton {
                        id: deleteBtn
                        text: "Eliminar zona"
                        variant: "danger"
                        onClicked: root.deleteRequested(root.zoneId)
                        objectName: "zoneDetailDeleteButton"
                        Accessible.name: "Eliminar zona " + root.zoneName + ". Esta acción no se puede deshacer."
                        Accessible.description: "Elimina permanentemente la zona"
                        KeyNavigation.backtab: renameBtn
                    }
                }
            }
        }

        degradedOverlay: Rectangle {
            color: Qt.rgba(1, 0.75, 0.14, 0.05)
            radius: MichiTheme.radiusMd
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
