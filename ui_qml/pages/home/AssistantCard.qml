import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Assistant Card"
    objectName: "assistantCard"
    focus: true
    id: root

    signal openAssistant()

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
            onClicked: root.openAssistant()
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
                    text: "Asistente Michi"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: "Pregunta sobre tu música, recibe sugerencias y controla tu biblioteca con IA."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.4
                }
            }

            MichiButton {
                anchors.verticalCenter: parent.verticalCenter
                text: "Abrir"
                variant: "ghost"
                onClicked: root.openAssistant()
            }
        }
    }
}
