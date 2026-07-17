import QtQuick
import QtQuick.Controls
import "../theme"

Slider {
    id: root
    objectName: "michiWarmSlider"

    property bool showThumb: enabled && (pressed || hovered || to > 0)
    property alias trackHeight: trackItem.height

    signal commit()

    from: 0
    to: 100
    stepSize: 0
    focusPolicy: Qt.StrongFocus
    activeFocusOnTab: enabled

    Accessible.role: Accessible.Slider
    Accessible.onIncreaseAction: increase()
    Accessible.onDecreaseAction: decrease()

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Left || event.key === Qt.Key_Down) { root.value = Math.max(root.from, root.value - (root.stepSize || 1)); event.accepted = true; root.commit() }
        else if (event.key === Qt.Key_Right || event.key === Qt.Key_Up) { root.value = Math.min(root.to, root.value + (root.stepSize || 1)); event.accepted = true; root.commit() }
        else if (event.key === Qt.Key_Home) { root.value = root.from; event.accepted = true; root.commit() }
        else if (event.key === Qt.Key_End) { root.value = root.to; event.accepted = true; root.commit() }
    }

    background: Rectangle {
        id: trackItem
        x: root.leftPadding
        y: root.topPadding + (root.availableHeight - height) / 2
        width: root.availableWidth
        height: 8
        radius: MichiTheme.radius.sm
        color: MichiTheme.colors.nowPlayingTrack

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: MichiTheme.colors.nowPlayingTrack
        }

        Rectangle {
            x: 0
            y: 0
            width: root.handle.visible ? root.handle.x + root.handle.width / 2 : root.visualPosition * parent.width
            height: parent.height
            radius: MichiTheme.radius.sm
            visible: root.enabled

            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: MichiTheme.colors.nowPlayingGradientStart }
                GradientStop { position: 0.33; color: MichiTheme.colors.nowPlayingGradientMiddle }
                GradientStop { position: 0.66; color: MichiTheme.colors.nowPlayingGradientEnd }
                GradientStop { position: 1.0; color: MichiTheme.colors.nowPlayingThumb }
            }
        }
    }

    handle: Rectangle {
        id: handleItem
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + (root.availableHeight - height) / 2
        width: 18
        height: 18
        radius: width / 2
        color: MichiTheme.colors.nowPlayingThumb
        border.width: 2
        border.color: MichiTheme.colors.nowPlayingThumbBorder
        visible: root.showThumb

        Rectangle {
            anchors.centerIn: parent
            width: 6
            height: 6
            radius: width / 2
            color: MichiTheme.colors.nowPlayingThumbBorder
            opacity: 0.5
        }
    }

    onPressedChanged: { if (!pressed) commit() }
}
