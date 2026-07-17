import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Suggestion Card"
    objectName: "suggestionCard"
    focus: true
    id: root

    property string suggestionTitle: ""
    property string suggestionDescription: ""
    property string actionRoute: ""

    signal actionTriggered()

    implicitHeight: 80
    width: parent ? parent.width : 400

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radius.sm
        hovered: mouseArea.containsMouse
        interactive: true

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.actionTriggered()
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 80
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.suggestionTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    elide: Text.ElideRight
                    width: parent.width
                }

                Text {
                    text: root.suggestionDescription
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    wrapMode: Text.WordWrap
                    width: parent.width
                    lineHeight: 1.3
                }
            }

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                anchors.verticalCenter: parent.verticalCenter
                text: "Abrir"
                variant: "ghost"
                onClicked: root.actionTriggered()
            }
        }
    }
}
