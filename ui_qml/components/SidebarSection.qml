import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    objectName: "sidebarSection"
    id: root

    property string text: ""
    property bool collapsed: false

    implicitHeight: collapsed ? 8 : 28
    implicitWidth: parent ? parent.width : 200

    Text {
        text: root.text
        color: MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.metaSize
        font.letterSpacing: 1.2
        visible: !root.collapsed
        anchors.left: parent.left
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.verticalCenter: parent.verticalCenter
    }
}
