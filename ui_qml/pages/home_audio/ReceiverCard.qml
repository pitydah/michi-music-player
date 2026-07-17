import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Receiver Card"
    objectName: "receiverCard"
    focus: true
    id: root

    property string receiverName: ""
    property string receiverRoom: ""
    property string receiverState: "disconnected"
    property string receiverType: ""

    signal configureClicked()

    implicitHeight: 100

    GlassMaterial {
        anchors.fill: parent
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radius.md

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
                    text: root.receiverName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: (root.receiverRoom !== "" ? root.receiverRoom + " · " : "") + root.receiverType
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                StatusBadge {
                    text: root.receiverState === "connected" ? "Activo" : "Inactivo"
                    kind: root.receiverState === "connected" ? "active" : "disconnected"
                }

                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: "Configurar"
                    variant: "ghost"
                    onClicked: root.configureClicked()
                }
            }
        }
    }
}
