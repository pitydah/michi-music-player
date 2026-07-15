import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property string serverName: ""
    property string serverHost: ""
    property int serverPort: 0
    property string state: "disconnected"
    property int latencyMs: 0
    property string contract: ""
    property string serverVersion: ""
    property string lastError: ""
    property var caps: []
    property string objectName: "connections.detailPage"

    signal backClicked()
    signal reconnectClicked()
    signal disconnectClicked()
    signal forgetServerClicked()
    signal editClicked()

    Accessible.role: Accessible.Panel
    Accessible.name: "Detalle de " + root.serverName
    Accessible.description: "Estado: " + root.state + ". Host: " + root.serverHost

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        objectName: root.objectName + ".flickable"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            MichiButton {
                id: backBtn
                text: "< Volver"
                variant: "ghost"
                onClicked: root.backClicked()
                objectName: root.objectName + ".backButton"
                Accessible.name: "Volver a conexiones"
            }

            Text {
                id: titleText
                text: root.serverName
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: root.objectName + ".title"
                Accessible.role: Accessible.Heading
                Accessible.name: root.serverName
            }

            GlassCard {
                id: statusCard
                width: parent.width
                title: "Estado"
                subtitle: "Detalles de conexión del servidor"
                objectName: root.objectName + ".statusCard"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Row {
                        spacing: MichiTheme.spacing.sm
                        Text { text: "Estado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        StatusBadge {
                            id: stateBadge
                            text: root.state === "connected" ? "Conectado" : root.state === "error" ? "Error" : root.state === "pairing_required" ? "Vinculación pendiente" : "Desconectado"
                            kind: root.state === "connected" ? "success" : root.state === "error" ? "error" : root.state === "pairing_required" ? "warning" : "disconnected"
                            objectName: root.objectName + ".stateBadge"
                        }
                    }

                    Text { text: "Host: " + root.serverHost + ":" + root.serverPort; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: root.objectName + ".host" }
                    Text { text: "Versión: " + root.serverVersion; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.serverVersion !== ""; objectName: root.objectName + ".version" }
                    Text { text: "Contrato: " + root.contract; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.contract !== ""; objectName: root.objectName + ".contract" }
                    Text { text: "Latencia: " + root.latencyMs + " ms"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.latencyMs > 0; objectName: root.objectName + ".latency" }
                }
            }

            ConnectionCapabilities {
                id: capsView
                width: parent.width
                capabilities: root.caps
                visible: root.caps.length > 0
                objectName: root.objectName + ".capabilities"
            }

            ConnectionErrorPanel {
                id: errorPanel
                width: parent.width
                errorText: root.lastError
                visible: root.lastError !== ""
                objectName: root.objectName + ".errorPanel"
                onRetryClicked: root.reconnectClicked()
                onDismissClicked: { }
            }

            Row {
                id: actionRow
                spacing: MichiTheme.spacing.sm
                objectName: root.objectName + ".actions"

                MichiButton {
                    id: reconnectBtn
                    text: "Reconectar"
                    variant: "primary"
                    onClicked: root.reconnectClicked()
                    objectName: root.objectName + ".reconnectButton"
                    Accessible.name: "Reconectar al servidor"
                }

                MichiButton {
                    id: disconnectBtn
                    text: "Desconectar"
                    variant: "secondary"
                    onClicked: root.disconnectClicked()
                    objectName: root.objectName + ".disconnectButton"
                    Accessible.name: "Desconectar del servidor"
                }

                MichiButton {
                    id: editBtn
                    text: "Editar"
                    variant: "ghost"
                    onClicked: root.editClicked()
                    objectName: root.objectName + ".editButton"
                    Accessible.name: "Editar configuración del servidor"
                }

                MichiButton {
                    id: forgetBtn
                    text: "Olvidar servidor"
                    variant: "danger"
                    onClicked: root.forgetServerClicked()
                    objectName: root.objectName + ".forgetButton"
                    Accessible.name: "Olvidar servidor. Esta acción eliminará la configuración guardada."
                }
            }
        }
    }
}
