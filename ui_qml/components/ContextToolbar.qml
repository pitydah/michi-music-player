import QtQuick
import "../theme"

FocusScope {
    id: root
    objectName: "contextToolbar"

    property string accessibleName: qsTr("Barra de herramientas contextual")
    default property alias content: contentHost.data

    implicitHeight: MichiTheme.toolbarHeight
    activeFocusOnTab: enabled && visible

    Accessible.role: Accessible.ToolBar
    Accessible.name: root.accessibleName

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceToolbar
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle
    }

    Item {
        id: contentHost
        anchors.fill: parent
    }

    Keys.onRightPressed: function(event) {
        root.nextItemInFocusChain(true).forceActiveFocus()
        event.accepted = true
    }
    Keys.onLeftPressed: function(event) {
        root.nextItemInFocusChain(false).forceActiveFocus()
        event.accepted = true
    }
}
