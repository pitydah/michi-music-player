import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Connection Detail"
    objectName: "connectionDetailPage"
    id: root
    focus: true

    property string connectionId: ""
    property string serverName: ""
    property string serverHost: ""
    property int serverPort: 0
    property string state: "disconnected"
    property int latencyMs: 0
    property string contract: ""
    property string serverVersion: ""
    property string lastError: ""
    property var caps: []
    property string protocol: "michi-link"
    property double lastContact: 0
    property bool compatible: false
    property var conn: typeof connectionsBridge !== "undefined" ? connectionsBridge : null

    signal backClicked()



    AsyncStateView {
        id: asyncView
        anchors.fill: parent
        state: root.state === "scanning" || root.state === "loading" ? AsyncStateView.LOADING
             : root.state === "error" ? AsyncStateView.ERROR
             : root.state === "unavailable" ? AsyncStateView.UNAVAILABLE
             : AsyncStateView.READY
        title: root.state === "error" ? "Error de conexión" : ""
        message: root.lastError
        details: "Servidor: " + root.serverName
        retryAvailable: root.state === "error"
        onRetryRequested: {
            if (root.conn) root.conn.retry()
        }

        readyContent: Flickable {
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
                    Accessible.role: Accessible.Button
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    KeyNavigation.tab: serverNameText
                    Keys.onReturnPressed: root.backClicked()
                    Keys.onSpacePressed: root.backClicked()
                }

                Text {
                    id: serverNameText
                    text: root.serverName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    KeyNavigation.tab: statusCard
                    KeyNavigation.backtab: backButton
                }

                GlassCard {
                    id: statusCard
                    width: parent.width
                    title: "Estado de conexión"
                    variant: "base"

                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Row {
                            spacing: MichiTheme.spacing.sm
                            width: parent.width
                            Text { text: "Estado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            StatusBadge {
                                text: {
                                    switch (root.state) {
                                        case "connected": return "Conectado"
                                        case "detected": return "Detectado"
                                        case "pairing_required": return "Vinculación pendiente"
                                        case "scanning": return "Escaneando"
                                        case "error": return "Error"
                                        default: return "Desconectado"
                                    }
                                }
                                kind: {
                                    switch (root.state) {
                                        case "connected": return "success"
                                        case "detected": return "info"
                                        case "pairing_required": return "warning"
                                        case "scanning": return "info"
                                        case "error": return "error"
                                        default: return "disconnected"
                                    }
                                }
                            }
                        }

                        Text { text: "Host: " + root.serverHost + ":" + root.serverPort; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        Text { text: "Protocolo: " + root.protocol; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.protocol !== "" }
                        Text { text: "Versión: " + root.serverVersion; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.serverVersion !== "" }
                        Text { text: "Contrato: " + root.contract; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.contract !== "" }
                        Text { text: "Latencia: " + root.latencyMs + " ms"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.latencyMs > 0 }
                        Text { text: "Último contacto: " + (root.lastContact > 0 ? new Date(root.lastContact * 1000).toLocaleString() : "Nunca"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.lastContact > 0 }

                        StatusBadge {
                            text: root.compatible ? "Compatible" : "Versión incompatible"
                            kind: root.compatible ? "success" : "warning"
                            visible: root.serverVersion !== ""
                        }
                    }
                }

                ConnectionCapabilities {
                    id: capsView
                    width: parent.width
                    capabilities: root.caps
                }

                ConnectionErrorPanel {
                    id: errorPanel
                    width: parent.width
                    errorText: root.lastError
                    visible: root.lastError !== ""
                    onRetryClicked: {
                        if (root.conn) root.conn.retry()
                    }
                    onDismissClicked: errorPanel.visible = false
                }

                Row {
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        id: testBtn
                        text: "Probar conexión"
                        variant: "secondary"
                        onClicked: {
                            if (root.conn && root.connectionId)
                                root.conn.testConnection(root.connectionId)
                        }
                        KeyNavigation.tab: reconnectBtn
                        KeyNavigation.backtab: errorPanel
                    }

                    MichiButton {
                        id: reconnectBtn
                        text: "Reconectar"
                        variant: "primary"
                        onClicked: {
                            if (root.conn && root.connectionId)
                                root.conn.reconnect(root.connectionId)
                            else if (root.conn)
                                root.conn.reconnect()
                        }
                        KeyNavigation.tab: disconnectBtn
                        KeyNavigation.backtab: testBtn
                    }

                    MichiButton {
                        id: disconnectBtn
                        text: "Desconectar"
                        variant: "secondary"
                        onClicked: {
                            if (root.conn) root.conn.disconnect()
                        }
                        KeyNavigation.tab: editBtn
                        KeyNavigation.backtab: reconnectBtn
                    }

                    MichiButton {
                        id: editBtn
                        text: "Editar"
                        variant: "ghost"
                        onClicked: {
                            if (root.conn && root.connectionId)
                                root.conn.editServer(root.connectionId)
                        }
                        KeyNavigation.tab: forgetBtn
                        KeyNavigation.backtab: disconnectBtn
                    }

                    MichiButton {
                        id: forgetBtn
                        text: "Eliminar"
                        variant: "danger"
                        onClicked: {
                            if (root.conn && root.connectionId) {
                                deleteConfirmDialog.open()
                            }
                        }
                        Accessible.description: "Elimina la configuración del servidor"
                        KeyNavigation.backtab: editBtn
                    }

                    QQC2.Dialog {
                        id: deleteConfirmDialog
                        title: "Eliminar servidor"
                        standardButtons: QQC2.Dialog.Yes | QQC2.Dialog.No
                        modal: true
                        x: Math.round((root.width - width) / 2)
                        y: Math.round((root.height - height) / 3)
                        parent: root
                        Text {
                            text: "¿Eliminar " + root.serverName + "?"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }
                        onAccepted: {
                            if (root.conn && root.connectionId)
                                root.conn.deleteServer(root.connectionId)
                        }
                    }
                }
            }
        }
    }
}
