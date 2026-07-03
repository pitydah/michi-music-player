import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    id: root

    property real from: 0
    property real to: 100
    property real value: 0
    property bool enabled: true

    signal moved()

    implicitHeight: 24
    radius: MichiTheme.radiusPill
    color: Qt.rgba(1,1,1,0.08)

    Rectangle {
        height: parent.height
        width: Math.max(0, Math.min(parent.width, (root.value - root.from) / Math.max(1, root.to - root.from) * parent.width))
        radius: MichiTheme.radiusPill
        color: root.enabled ? MichiTheme.colors.accentBlue : Qt.rgba(1,1,1,MichiTheme.opacityDisabled)
    }

    Rectangle {
        x: Math.max(0, Math.min(parent.width - 8, (root.value - root.from) / Math.max(1, root.to - root.from) * parent.width - 4))
        y: (parent.height - 8) / 2
        width: 8
        height: 8
        radius: 4
        color: root.enabled ? Qt.rgba(1,1,1,0.9) : Qt.rgba(1,1,1,MichiTheme.opacityDisabled)
        visible: root.enabled
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onPressed: function(mouse) { _update(mouse.x) }
        onPositionChanged: function(mouse) { _update(mouse.x) }
        function _update(mx) {
            var ratio = Math.max(0, Math.min(1, mx / parent.width))
            root.value = root.from + ratio * (root.to - root.from)
            root.moved()
        }
    }
}
