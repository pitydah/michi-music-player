import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string serverName: ""
    property string serverHost: ""
    property string serverType: ""
    property string statusText: "Conectado"
    property string statusKind: "success"
    property string objectName: "configuredServerCard"

    signal disconnectClicked()
    signal configureClicked()

    implicitHeight: 100

    Accessible.role: Accessible.ListItem
    Accessible.name: root.serverName
    Accessible.description: "Estado: " + root.statusText + ". Tipo: " + root.serverType

    GlassMaterial {
        anchors.fill: parent
        variant: "elevated"
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

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 200
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

                StatusBadge { text: root.statusText; kind: root.statusKind; objectName: root.objectName + ".statusBadge" }

                MichiButton {
                    text: "Configurar"
                    variant: "secondary"
                    onClicked: root.configureClicked()
                    objectName: root.objectName + ".configureButton"
                    Accessible.name: "Configurar " + root.serverName
                }

                MichiButton {
                    text: "Desconectar"
                    variant: "ghost"
                    onClicked: root.disconnectClicked()
                    objectName: root.objectName + ".disconnectButton"
                    Accessible.name: "Desconectar " + root.serverName
                }
            }
        }
    }
}
