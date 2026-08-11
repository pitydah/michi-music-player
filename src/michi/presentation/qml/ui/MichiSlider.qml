import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Slider {
    id: root

    implicitHeight: MichiTheme.controlHeightSmall

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        implicitWidth: 200
        implicitHeight: 4
        width: root.availableWidth
        height: implicitHeight
        radius: 2
        color: MichiTheme.surfaceHover

        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: root.enabled ? MichiTheme.accent : MichiTheme.textDisabled
        }
    }

    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        implicitWidth: 14
        implicitHeight: 14
        radius: 7
        color: {
            if (!root.enabled) return MichiTheme.textDisabled
            if (root.pressed) return MichiTheme.accentPressed
            if (root.hovered || root.visualFocus) return MichiTheme.accentHover
            return MichiTheme.accent
        }
    }
}
