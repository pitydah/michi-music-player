import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Error State"
    objectName: "libraryErrorState"
    focus: true
    id: root

    property string title: "Error al cargar la biblioteca"
    property string message: "Ocurrió un problema al obtener los datos. Verifica tu conexión o la configuración de fuentes."
    property string actionText: "Reintentar"

    signal actionRequested()

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.lg
        width: Math.min(400, parent.width - 40)

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 64; height: 64; radius: 16
            color: MichiTheme.colors.error
            opacity: MichiTheme.opacity.muted
            Text {
                anchors.centerIn: parent
                text: "!"
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.heroTitleSize
                font.weight: MichiTheme.typography.weightBold
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        MichiButton {
            objectName: "errorStateActionButton"
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.actionText
            variant: "primary"
            onClicked: root.actionRequested()
        }
    }
}
