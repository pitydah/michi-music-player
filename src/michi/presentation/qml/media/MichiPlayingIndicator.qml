import QtQuick
import QtQuick.Layouts
import "../theme"

RowLayout {
    id: root
    property bool playing: false
    property color indicatorColor: MichiPalette.auroraCyan
    spacing: 2
    implicitWidth: 14
    implicitHeight: 14
    Repeater {
        model: 3
        Rectangle {
            required property int index
            width: 2
            radius: 1
            color: root.indicatorColor
            Layout.alignment: Qt.AlignBottom
            height: root.playing ? 5 + index * 2 : 3
            SequentialAnimation on height {
                running: root.playing && !MichiAccessibility.reducedMotion
                loops: Animation.Infinite
                NumberAnimation { to: 12 - index * 2; duration: 170 + index * 40; easing.type: Easing.InOutCubic }
                NumberAnimation { to: 4 + index * 2; duration: 170 + index * 40; easing.type: Easing.InOutCubic }
            }
        }
    }
}
