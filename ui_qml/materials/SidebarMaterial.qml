import QtQuick
import "../theme"

Item {
    id: root

    property int radius: 0

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceSidebar

        Rectangle {
            anchors.right: parent.right
            width: MichiTheme.borderWidth
            height: parent.height
            color: MichiTheme.colors.borderSubtle
        }
    }
}
