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

    signal backClicked()
    signal reconnectClicked()
    signal disconnectClicked()
    signal forgetServerClicked()
    signal editClicked()
    signal retryClicked()

    objectName: "connectionDetailPage"

    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle de conexión"

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
        onRetryRequested: root.retryClicked()

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true
            objectName: "connectionDetailFlickable"

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                MichiButton {
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "detailBackButton"
                    Accessible.name: "Volver a conexiones"
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
                    Accessible.name: "Servidor: " + root.serverName
                    objectName: "detailServerName"
                    KeyNavigation.tab: statusCard
                    KeyNavigation.backtab: backButton
                }

                GlassCard {
                    id: statusCard
                    width: parent.width
                    title: "Estado de conexión"
                    variant: "base"
                    objectName: "detailStatusCard"
                    Accessible.name: "Estado de conexión"

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
                    objectName: "detailCapabilities"
                    Accessible.name: "Capacidades del servidor"
                }

                ConnectionErrorPanel {
                    id: errorPanel
                    width: parent.width
                    errorText: root.lastError
                    visible: root.lastError !== ""
                    objectName: "detailErrorPanel"
                    onRetryClicked: root.retryClicked()
                    onDismissClicked: errorPanel.visible = false
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    objectName: "detailActions"
                    Accessible.name: "Acciones de conexión"

                    MichiButton {
                        id: reconnectBtn
                        text: "Reconectar"
                        variant: "primary"
                        onClicked: root.reconnectClicked()
                        objectName: "detailReconnectButton"
                        Accessible.name: "Reconectar servidor"
                        KeyNavigation.tab: disconnectBtn
                        KeyNavigation.backtab: errorPanel
                    }

                    MichiButton {
                        id: disconnectBtn
                        text: "Desconectar"
                        variant: "secondary"
                        onClicked: root.disconnectClicked()
                        objectName: "detailDisconnectButton"
                        Accessible.name: "Desconectar servidor"
                        KeyNavigation.tab: editBtn
                        KeyNavigation.backtab: reconnectBtn
                    }

                    MichiButton {
                        id: editBtn
                        text: "Editar"
                        variant: "ghost"
                        onClicked: root.editClicked()
                        objectName: "detailEditButton"
                        Accessible.name: "Editar configuración del servidor"
                        KeyNavigation.tab: forgetBtn
                        KeyNavigation.backtab: disconnectBtn
                    }

                    MichiButton {
                        id: forgetBtn
                        text: "Olvidar servidor"
                        variant: "danger"
                        onClicked: root.forgetServerClicked()
                        objectName: "detailForgetButton"
                        Accessible.name: "Olvidar servidor. Esta acción no se puede deshacer."
                        Accessible.description: "Elimina la configuración del servidor"
                        KeyNavigation.backtab: editBtn
                    }
                }
            }
        }
    }
}
