import QtQuick
import QtQuick.Layouts
import "../theme"

/*
    M10.3 route scaffold only.
    M10.4 will replace this placeholder with real settings controls.
*/

Item {
    ColumnLayout {
        anchors.centerIn: parent
        spacing: MichiTheme.space12

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Settings"
            font.pixelSize: MichiTheme.fontSizeTitle
            font.weight: MichiTheme.fontWeightBold
            color: MichiTheme.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Settings interface will be implemented in M10.4"
            font.pixelSize: MichiTheme.fontSizeBody
            color: MichiTheme.textSecondary
        }
    }
}
