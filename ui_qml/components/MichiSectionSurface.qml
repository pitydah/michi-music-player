import QtQuick
import "../theme"

/* MichiSectionSurface — groups related content without per-item cards. */
Item {
    id: root
    property int radius: MichiTheme.radius.md

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiTheme.colors.surfaceElevation1
        border.color: MichiTheme.colors.borderSubtle
        border.width: 1
    }
}
