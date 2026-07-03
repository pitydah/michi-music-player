import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string serverName: ""
    property string serverHost: ""
    property string serverType: ""
    property string serverStatus: "disconnected"

    signal connectClicked()

    implicitHeight: 100

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

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 160
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.serverName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.serverHost + " · " + root.serverType
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                StatusBadge {
                    text: root.serverStatus === "connected" ? "Conectado"
                        : root.serverStatus === "detected" ? "Detectado"
                        : "Desconectado"
                    kind: root.serverStatus === "connected" ? "success"
                        : root.serverStatus === "detected" ? "info"
                        : "disconnected"
                }

                ActionButton {
                    text: "Conectar"
                    variant: "accent"
                    onClicked: root.connectClicked()
                }
            }
        }
    }
}
