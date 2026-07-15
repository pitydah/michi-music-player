import QtQuick
import QtQuick.Controls
import "../theme"
import "foundations"

Item {
    id: root

    property string title: "Cargando"
    property string message: ""
    property string objectName: "loadingState"
    property bool reducedMotion: MichiReducedMotion.enabled

    Accessible.role: Accessible.Indicator
    Accessible.name: root.title
    Accessible.description: root.message

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.md
        width: Math.min(implicitWidth, 320)

        BusyIndicator {
            id: spinner
            anchors.horizontalCenter: parent.horizontalCenter
            running: true
            Accessible.role: Accessible.Indicator
            Accessible.name: root.title
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightMedium
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }
    }
}
