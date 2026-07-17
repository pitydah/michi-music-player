import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Configured Server Card"
    objectName: "configuredServerCard"
    focus: true
    id: root

    property string serverName: ""
    property string serverHost: ""
    property string serverType: ""
    property string statusText: "Conectado"
    property string statusKind: "success"

    signal disconnectClicked()
    signal configureClicked()

    implicitHeight: 100

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

                StatusBadge { text: root.statusText; kind: root.statusKind }

                MichiButton {
                    Accessible.role: Accessible.Button
                    text: "Configurar"
                    variant: "secondary"
                    onClicked: root.configureClicked()
                }
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true


                MichiButton {
                    text: "Desconectar"
                    variant: "ghost"
                    onClicked: root.disconnectClicked()
                }
            }
        }
    }
}
