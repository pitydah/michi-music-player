import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Home Audio Access"
    objectName: "homeAudioAccess"
    focus: true
    id: root

    signal openHomeAudio()

    implicitHeight: 80

    GlassMaterial {
        anchors.fill: parent
        variant: "primary"
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radius.md

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openHomeAudio()
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 120
                spacing: MichiTheme.spacing.xs

                Text {
                    text: qsTr("Home Audio")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: qsTr("Home Assistant y Michi Music Stream en tu hogar")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Abrir")
                variant: "primary"
                onClicked: root.openHomeAudio()
            }
        }
    }
}
