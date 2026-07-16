import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sidebar Material"
    objectName: "sidebarMaterial"
    focus: true
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
