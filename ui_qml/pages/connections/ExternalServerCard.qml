import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string serverName: ""
    property string serverType: ""
    property string badgeText: "Externo"
    property string badgeKind: "info"
    property string objectName: "connections.externalCard"

    signal configureClicked()

    implicitHeight: 80

    Accessible.role: Accessible.ListItem
    Accessible.name: root.serverName
    Accessible.description: "Tipo: " + root.serverType

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

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 140
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.serverName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    objectName: root.objectName + ".name"
                }

                Text {
                    text: root.serverType
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    objectName: root.objectName + ".type"
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                StatusBadge { text: root.badgeText; kind: root.badgeKind }

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
