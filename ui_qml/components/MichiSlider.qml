import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    id: root

    property real from: 0
    property real to: 100
    property real value: 0
    property real stepSize: 1
    property bool hovered: ma.containsMouse
    property bool pressed: ma.pressed

    signal moved(real value)

    implicitHeight: 24
    radius: MichiTheme.radiusPill
    color: root.activeFocus
        ? Qt.rgba(0.56, 0.72, 1.0, 0.18)
        : (root.hovered ? Qt.rgba(1,1,1,0.12) : Qt.rgba(1,1,1,0.08))
    opacity: root.enabled ? 1.0 : MichiTheme.opacityDisabled
    focus: root.enabled
    activeFocusOnTab: root.enabled

    function _range() {
        return Math.max(0.0001, root.to - root.from)
    }

    function _ratioForValue(v) {
        return Math.max(0, Math.min(1, (v - root.from) / root._range()))
    }

    function _clamp(v) {
        return Math.max(root.from, Math.min(root.to, v))
    }

    function _setValue(v, emitMoved) {
        var next = root._clamp(v)
        if (Math.abs(next - root.value) > 0.0001)
            root.value = next
        if (emitMoved)
            root.moved(root.value)
    }

    function _setFromPosition(mx) {
        var ratio = Math.max(0, Math.min(1, mx / Math.max(1, root.width)))
        root._setValue(root.from + ratio * root._range(), true)
    }

    function _step(delta) {
        root._setValue(root.value + delta, true)
    }

    onFromChanged: root._setValue(root.value, false)
    onToChanged: root._setValue(root.value, false)
    onValueChanged: root.value = root._clamp(root.value)

    Keys.onLeftPressed: function(event) {
        if (!root.enabled) return
        root._step(-root.stepSize)
        event.accepted = true
    }

    Keys.onRightPressed: function(event) {
        if (!root.enabled) return
        root._step(root.stepSize)
        event.accepted = true
    }

    Keys.onDownPressed: function(event) {
        if (!root.enabled) return
        root._step(-root.stepSize)
        event.accepted = true
    }

    Keys.onUpPressed: function(event) {
        if (!root.enabled) return
        root._step(root.stepSize)
        event.accepted = true
    }

    Rectangle {
        height: parent.height
        width: root._ratioForValue(root.value) * parent.width
        radius: MichiTheme.radiusPill
        color: root.enabled ? MichiTheme.colors.accentBlue : Qt.rgba(1,1,1,MichiTheme.opacityDisabled)
    }

    Rectangle {
        x: Math.max(0, Math.min(parent.width - width, root._ratioForValue(root.value) * parent.width - width / 2))
        y: (parent.height - height) / 2
        width: root.pressed || root.activeFocus ? 12 : 8
        height: width
        radius: width / 2
        color: root.enabled ? Qt.rgba(1,1,1,0.9) : Qt.rgba(1,1,1,MichiTheme.opacityDisabled)
        visible: root.enabled
        Behavior on width { NumberAnimation { duration: MichiTheme.motion.fast } }
    }

    MouseArea {
        id: ma
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onPressed: function(mouse) {
            root.forceActiveFocus()
            root._setFromPosition(mouse.x)
        }
        onPositionChanged: function(mouse) {
            if (pressed)
                root._setFromPosition(mouse.x)
        }
    }
}
