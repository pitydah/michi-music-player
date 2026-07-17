import QtQuick
import "../theme"

Item {
    id: root

    property var model: []
    property int currentIndex: 0
    property string accessibleName: "Selector de vista"

    signal activated(int index)

    implicitHeight: 36
    implicitWidth: parent ? parent.width : 400

    Accessible.role: Accessible.PageTabList
    Accessible.name: root.accessibleName

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceInput
        radius: MichiTheme.radius.md

        Row {
            anchors.fill: parent
            spacing: 2

            Repeater {
                model: root.model

                Item {
                    width: parent.width / root.model.length
                    height: parent.height

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: MichiTheme.radius.sm
                        color: index === root.currentIndex ? MichiTheme.colors.surfaceElevation2 : "transparent"

                        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: index === root.currentIndex ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.secondarySize
                            font.weight: index === root.currentIndex ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.currentIndex = index
                            root.activated(index)
                        }
                    }

                    Accessible.role: Accessible.PageTab
                    Accessible.name: modelData
                    Accessible.selected: index === root.currentIndex
                }
            }
        }
    }

    Keys.onLeftPressed: {
        var prev = Math.max(0, root.currentIndex - 1)
        root.currentIndex = prev
        root.activated(prev)
    }

    Keys.onRightPressed: {
        var next = Math.min(root.model.length - 1, root.currentIndex + 1)
        root.currentIndex = next
        root.activated(next)
    }
}
