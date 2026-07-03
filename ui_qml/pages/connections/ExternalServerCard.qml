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

    signal configureClicked()

    implicitHeight: 80

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
                width: parent.width - 140
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.serverName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.serverType
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                StatusBadge { text: root.badgeText; kind: root.badgeKind }

                ActionButton {
                    text: "Configurar"
                    variant: "ghost"
                    onClicked: root.configureClicked()
                }
            }
        }
    }
}
