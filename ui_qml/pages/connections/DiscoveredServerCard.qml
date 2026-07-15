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
    property string objectName: "discoveredServerCard"

    signal connectClicked()

    implicitHeight: 100

    Accessible.role: Accessible.ListItem
    Accessible.name: root.serverName
    Accessible.description: "Estado: " + root.serverStatus + ". Host: " + root.serverHost

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
            onClicked: root.connectClicked()
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
                    objectName: root.objectName + ".name"
                }

                Text {
                    text: root.serverHost + " · " + root.serverType
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    objectName: root.objectName + ".host"
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
                    objectName: root.objectName + ".statusBadge"
                }

                MichiButton {
                    text: "Conectar"
                    variant: "accent"
                    onClicked: root.connectClicked()
                    objectName: root.objectName + ".connectButton"
                    Accessible.name: "Conectar a " + root.serverName
                }
            }
        }
    }
}
