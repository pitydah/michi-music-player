import QtQuick
import "../../theme"
import "../../materials"
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
    property bool compatible: false
    property string objectName: "connections.card"

    signal connectClicked()
    signal disconnectClicked()
    signal configureClicked()

    implicitHeight: 120

    Accessible.role: Accessible.ListItem
    Accessible.name: root.serverName
    Accessible.description: "Estado: " + root.state + ". Host: " + root.serverHost

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
            onClicked: root.configureClicked()
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.md

                Column {
                    width: parent.width - 200
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: root.serverName
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                        width: parent.width
                        objectName: root.objectName + ".name"
                    }

                    Text {
                        text: root.serverHost + ":" + root.serverPort
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
                        objectName: root.objectName + ".host"
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    anchors.verticalCenter: parent.verticalCenter

                    StatusBadge {
                        id: stateBadge
                        text: {
                            switch (root.state) {
                                case "connected": return "Conectado"
                                case "detected": return "Detectado"
                                case "pairing_required": return "Vinculación"
                                case "error": return "Error"
                                default: return "Desconectado"
                            }
                        }
                        kind: {
                            switch (root.state) {
                                case "connected": return "success"
                                case "detected": return "info"
                                case "pairing_required": return "warning"
                                case "error": return "error"
                                default: return "disconnected"
                            }
                        }
                        objectName: root.objectName + ".statusBadge"
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.md

                Text {
                    text: root.latencyMs > 0 ? root.latencyMs + " ms" : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: root.latencyMs > 0
                }

                Text {
                    text: root.serverVersion
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: root.serverVersion !== ""
                }

                StatusBadge {
                    text: root.compatible ? "Compatible" : "Versión antigua"
                    kind: root.compatible ? "success" : "warning"
                    visible: root.serverVersion !== ""
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: root.state === "connected" ? "Desconectar" : "Conectar"
                    variant: root.state === "connected" ? "secondary" : "primary"
                    onClicked: root.state === "connected" ? root.disconnectClicked() : root.connectClicked()
                    objectName: root.objectName + ".connectButton"
                    Accessible.name: root.state === "connected" ? "Desconectar " + root.serverName : "Conectar " + root.serverName
                }

                MichiButton {
                    text: "Configurar"
                    variant: "ghost"
                    onClicked: root.configureClicked()
                    objectName: root.objectName + ".configureButton"
                    Accessible.name: "Configurar " + root.serverName
                }
            }
        }
    }
}
