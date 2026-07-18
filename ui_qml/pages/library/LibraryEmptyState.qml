import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Empty State"
    objectName: "libraryEmptyState"
    focus: true
    id: root

    property string title: qsTr("Biblioteca vacía")
    property string message: qsTr("Agrega carpetas con música o refresca la biblioteca.")
    property string actionText: "Refrescar"

    signal actionRequested()

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.lg
        width: Math.min(400, parent.width - 40)

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: MichiTheme.coverSizeMedium; height: MichiTheme.coverSizeMedium; radius: MichiTheme.radius.xl
            color: MichiTheme.colors.accentSurface
            Text {
                anchors.centerIn: parent
                text: qsTr("BL")
                color: MichiTheme.colors.accentBlue
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightBold
                opacity: MichiTheme.opacity.hover
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

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.sm

            MichiButton { objectName: qsTr("emptyStateActionButton"); text: root.actionText; variant: "primary"; onClicked: root.actionRequested() }
            MichiButton { text: qsTr("Ajustes"); variant: "ghost"; onClicked: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("settings") } }
        }
    }
}
