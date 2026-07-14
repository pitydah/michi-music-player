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

    signal backClicked()
    signal reconnectClicked()
    signal disconnectClicked()
    signal forgetServerClicked()
    signal editClicked()

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

            Text {
                text: root.serverName
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            GlassCard {
                width: parent.width
                title: "Estado"
                subtitle: "Detalles de conexión del servidor"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Row {
                        spacing: MichiTheme.spacing.sm
                        Text { text: "Estado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        StatusBadge {
                            text: root.state
                            kind: root.state === "connected" ? "success" : root.state === "error" ? "error" : "disconnected"
                        }
                    }

                    Text { text: "Host: " + root.serverHost + ":" + root.serverPort; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                    Text { text: "Versión: " + root.serverVersion; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.serverVersion !== "" }
                    Text { text: "Contrato: " + root.contract; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.contract !== "" }
                    Text { text: "Latencia: " + root.latencyMs + " ms"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.latencyMs > 0 }
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
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton { text: "Reconectar"; variant: "primary"; onClicked: root.reconnectClicked() }
                MichiButton { text: "Desconectar"; variant: "secondary"; onClicked: root.disconnectClicked() }
                MichiButton { text: "Editar"; variant: "ghost"; onClicked: root.editClicked() }
                MichiButton { text: "Olvidar servidor"; variant: "danger"; onClicked: root.forgetServerClicked() }
            }
        }
    }
}
