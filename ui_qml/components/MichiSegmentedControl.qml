import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property var model: []
    property int currentIndex: 0
    property string accessibleName: "Selector de vista"

    signal activated(int index)

    implicitHeight: MichiTheme.minimumInteractiveSize
    implicitWidth: parent ? parent.width : 400

    Accessible.role: Accessible.PageTabList
    Accessible.name: root.accessibleName

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceInput
        radius: MichiTheme.radius.md
        border.width: MichiTheme.borderWidth
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus
                                      : MichiTheme.colors.borderCard

        Row {
            anchors.fill: parent
            spacing: 2

            Repeater {
                model: root.model

                AbstractButton {
                    id: segment
                    width: parent.width / root.model.length
                    height: parent.height
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    activeFocusOnTab: index === root.currentIndex
                    Accessible.role: Accessible.PageTab
                    Accessible.name: modelData
                    Accessible.selected: index === root.currentIndex

                    onClicked: {
                        root.currentIndex = index
                        root.activated(index)
                    }

                    background: Rectangle {
                        anchors.fill: parent
                        anchors.margins: 4
                        radius: MichiTheme.radius.sm
                        color: segment.down ? MichiTheme.colors.surfacePressed
                             : index === root.currentIndex ? MichiTheme.colors.accentSurface
                             : segment.hovered ? MichiTheme.colors.surfaceHover : "transparent"
                        border.width: segment.activeFocus ? MichiTheme.focusWidth
                                                        : index === root.currentIndex ? MichiTheme.borderWidth : 0
                        border.color: segment.activeFocus ? MichiTheme.colors.borderFocus
                                                        : MichiTheme.colors.borderHover

                        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
                    }

                    contentItem: Text {
                        text: modelData
                        color: index === root.currentIndex ? MichiTheme.colors.textPrimary
                                                          : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        font.weight: index === root.currentIndex
                                     ? MichiTheme.typography.weightSemiBold
                                     : MichiTheme.typography.weightMedium
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
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
