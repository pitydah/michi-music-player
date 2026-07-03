import QtQuick
import "../theme"

Item {
    id: root

    property int radius: MichiTheme.radiusLg

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiTheme.colors.surfacePopup
        border.color: MichiTheme.colors.borderActive
        border.width: MichiTheme.borderWidth
    }
}
