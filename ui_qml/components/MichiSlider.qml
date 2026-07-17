import QtQuick
import "../theme"

Rectangle {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property real from: 0
    property real to: 100
    property real value: 0
    property real stepSize: 1
    property bool hovered: ma.containsMouse
    property bool pressed: ma.pressed
    property bool loading: false
    property bool reducedMotion: false
    property string accessibleName: "Valor: " + Math.round(root.value) + " de " + Math.round(root.to)
    property string accessibleDescription: ""

    signal moved(real value)

    implicitHeight: MichiTheme.minimumInteractiveSize
    radius: MichiTheme.radius.pill
    color: root.activeFocus ? MichiTheme.colors.focusHalo
           : (root.hovered ? MichiTheme.colors.surfacePressed : MichiTheme.colors.controlTrack)
    opacity: root.enabled ? 1.0 : MichiTheme.opacity.disabled
    activeFocusOnTab: enabled
    enabled: !root.loading

    Accessible.role: Accessible.Slider
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription
    Accessible.onIncreaseAction: root._step(root.stepSize)
    Accessible.onDecreaseAction: root._step(-root.stepSize)

    function _range() {
        return Math.max(0.0001, root.to - root.from)
    }

    function _ratioForValue(v) {
        return Math.max(0, Math.min(1, (v - root.from) / root._range()))
    }

    function _clamp(v) {
        return Math.max(root.from, Math.min(root.to, v))
    }

    function setClampedValue(candidate, emitSignal) {
        var nextValue = Math.max(root.from, Math.min(root.to, candidate))
        if (nextValue !== root.value) root.value = nextValue
        if (emitSignal) root.moved(nextValue)
    }

    function _step(delta) {
        root.setClampedValue(root.value + delta, true)
    }

    function _setFromPosition(mx) {
        var ratio = Math.max(0, Math.min(1, mx / Math.max(1, root.width)))
        root.setClampedValue(root.from + ratio * root._range(), true)
    }

    onFromChanged: root.setClampedValue(root.value, false)
    onToChanged: root.setClampedValue(root.value, false)

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

    Keys.onPressed: function(event) {
        if (!root.enabled) return
        if (event.key === Qt.Key_Home) {
            root.setClampedValue(root.from, true)
            event.accepted = true
        } else if (event.key === Qt.Key_End) {
            root.setClampedValue(root.to, true)
            event.accepted = true
        }
    }

    Rectangle {
        height: parent.height
        width: root._ratioForValue(root.value) * parent.width
        radius: MichiTheme.radius.pill
        color: root.enabled ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
    }

    Rectangle {
        x: Math.max(0, Math.min(parent.width - width, root._ratioForValue(root.value) * parent.width - width / 2))
        y: (parent.height - height) / 2
        width: root.pressed || root.activeFocus ? 12 : 8
        height: width
        radius: width / 2
        color: root.enabled ? MichiTheme.colors.controlThumb : MichiTheme.colors.textMuted
        visible: root.enabled
        Behavior on width {
            NumberAnimation {
                duration: root.reducedMotion ? 0 : MichiTheme.motion.durationFast
                easing.type: Easing.OutCubic
            }
        }
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
