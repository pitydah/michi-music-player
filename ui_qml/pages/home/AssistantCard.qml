import QtQuick
import QtQuick.Layouts
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

    implicitHeight: 112

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

        RowLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Asistente Michi")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: qsTr("Pregunta sobre tu música, recibe sugerencias y controla tu biblioteca con IA.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                Layout.alignment: Qt.AlignVCenter
                text: qsTr("Abrir")
                variant: "ghost"
                onClicked: root.openAssistant()
            }
        }
    }
}
