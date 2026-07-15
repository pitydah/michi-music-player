import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string objectName: "connections.homeAudioAccess"

    signal openHomeAudio()

    implicitHeight: 80

    Accessible.role: Accessible.Button
    Accessible.name: "Acceso a Home Audio"
    Accessible.description: "Home Assistant y Michi Music Stream en tu hogar"

    GlassMaterial {
        anchors.fill: parent
        variant: "accent"
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radiusMd

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
                    text: "Home Audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    objectName: root.objectName + ".title"
                }

                Text {
                    text: "Home Assistant y Michi Music Stream en tu hogar"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    objectName: root.objectName + ".subtitle"
                }
            }

            MichiButton {
                anchors.verticalCenter: parent.verticalCenter
                text: "Abrir"
                variant: "accent"
                onClicked: root.openHomeAudio()
                objectName: root.objectName + ".openButton"
                Accessible.name: "Abrir Home Audio"
            }
        }
    }
}
