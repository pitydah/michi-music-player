import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property bool serverActive: false
    property int serverPort: 53318
    property int peerCount: 0

    signal startServer()
    signal stopServer()

    implicitHeight: 120

    objectName: "SyncStatusPanel"
    Accessible.role: Accessible.Pane
    Accessible.name: "Estado del servidor de sincronización"

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        variant: root.serverActive ? "accent" : "base"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Row {
                width: parent.width; spacing: MichiTheme.spacing.sm
                Text {
                    text: "Servidor Sync"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    objectName: "syncServerTitle"
                    Accessible.name: "Servidor de sincronización"
                }
                StatusBadge {
                    id: serverStatusBadge
                    text: root.serverActive ? "Activo" : "Inactivo"
                    kind: root.serverActive ? "active" : "disconnected"
                    objectName: "serverStatusBadge"
                    Accessible.name: text
                }
            }

            Text {
                text: root.serverActive
                    ? "Puerto " + root.serverPort + " · " + root.peerCount + " peer(s) detectados"
                    : "Servidor de sincronización detenido"
                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                objectName: "syncServerDetail"
                Accessible.name: text
            }

            MichiButton {
                id: toggleServerButton
                text: root.serverActive ? "Detener servidor" : "Iniciar servidor"
                variant: root.serverActive ? "secondary" : "primary"
                onClicked: root.serverActive ? root.stopServer() : root.startServer()
                objectName: "toggleServerButton"
                Accessible.name: root.serverActive ? "Detener servidor de sincronización" : "Iniciar servidor de sincronización"
            }
        }
    }
}
