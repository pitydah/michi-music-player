import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Popup Material"
    objectName: "popupMaterial"
    focus: true
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
