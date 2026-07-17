import QtQuick
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property var model: []
    property int currentIndex: 0
    property bool loading: false
    property string accessibleName: "Barra de pesta\u00F1as"
    property string accessibleDescription: ""

    signal activated(int index)

    implicitHeight: MichiTheme.minimumInteractiveSize
    implicitWidth: parent ? parent.width : 400
    activeFocusOnTab: enabled && visible

    Accessible.role: Accessible.PageTabList
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    Row {
        anchors.fill: parent
        spacing: 0

        Repeater {
            model: root.model

            Item {
                width: Math.max(1, parent.width / root.model.length)
                height: parent.height
                property bool isActive: index === root.currentIndex
                property bool isHovered: tabMa.containsMouse

                Rectangle {
                    anchors.fill: parent
                    radius: 0
                    color: isActive ? "transparent" : (isHovered ? MichiTheme.colors.surfaceHover : "transparent")

                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 2
                        color: isActive ? MichiTheme.colors.accentBlue : "transparent"

                        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    radius: MichiTheme.radius.sm
                    color: "transparent"
                    border.width: root.activeFocus && isActive ? MichiTheme.focusWidth : 0
                    border.color: MichiTheme.colors.borderFocus
                }

                Text {
                    anchors.centerIn: parent
                    text: modelData
                    color: isActive ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: isActive ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                    elide: Text.ElideRight
                }

                MouseArea {
                    id: tabMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    enabled: !root.loading
                    onClicked: {
                        root.currentIndex = index
                        root.activated(index)
                    }
                }

                Accessible.role: Accessible.PageTab
                Accessible.name: modelData
                Accessible.selected: isActive
            }
        }
    }

    Keys.onLeftPressed: function(event) {
        var prev = Math.max(0, root.currentIndex - 1)
        root.currentIndex = prev
        root.activated(prev)
        event.accepted = true
    }

    Keys.onRightPressed: function(event) {
        var next = Math.min(root.model.length - 1, root.currentIndex + 1)
        root.currentIndex = next
        root.activated(next)
        event.accepted = true
    }

    Keys.onHomePressed: function(event) {
        root.currentIndex = 0
        root.activated(0)
        event.accepted = true
    }

    Keys.onEndPressed: function(event) {
        root.currentIndex = root.model.length - 1
        root.activated(root.currentIndex)
        event.accepted = true
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: MichiTheme.colors.borderCard
        z: -1
    }
}
