import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sidebar Material"
    objectName: "sidebarMaterial"
    focus: true
    id: root

    default property alias content: contentLayer.data

    property int radius: 0

    Item {
        id: backgroundLayer
        anchors.fill: parent
        z: 0
        enabled: false

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

    Item {
        id: contentLayer
        anchors.fill: parent
        z: 1
    }
}
