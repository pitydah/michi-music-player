import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Popup Material"
    objectName: "popupMaterial"
    id: root

    property int radius: MichiTheme.radius.lg

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiTheme.colors.surfaceGlassStrong
        border.color: MichiTheme.colors.borderCard
        border.width: MichiTheme.borderWidth

        Rectangle {
            anchors.fill: parent
            anchors.margins: MichiTheme.borderWidth
            radius: Math.max(0, parent.radius - MichiTheme.borderWidth)
            color: "transparent"
            border.color: MichiTheme.colors.surfaceEdgeHighlight
            border.width: MichiTheme.borderWidth
        }
    }
}
