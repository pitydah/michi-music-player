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

    signal connectClicked()
    signal disconnectClicked()
    signal configureClicked()

    implicitHeight: 120

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
                    }

                    Text {
                        text: root.serverHost + ":" + root.serverPort
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    anchors.verticalCenter: parent.verticalCenter

                    StatusBadge {
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
                }

                MichiButton {
                    text: "Configurar"
                    variant: "ghost"
                    onClicked: root.configureClicked()
                }
            }
        }
    }
}
