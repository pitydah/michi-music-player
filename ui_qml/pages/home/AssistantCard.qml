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

    implicitHeight: MichiTheme.density.comfortable + MichiTheme.spacing.xl * 2

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
                    text: qsTr("Asistente Michi")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: qsTr("Pregunta sobre tu música, recibe sugerencias y controla tu biblioteca con IA.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.4
                }
            }

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Abrir")
                variant: "ghost"
                onClicked: root.openAssistant()
            }
        }
    }
}
