import QtQuick
import QtQuick.Controls.Basic
import "../theme"

ScrollBar {
    id: root
    policy: ScrollBar.AsNeeded
    implicitWidth: 8
    implicitHeight: 8
    padding: 2
    contentItem: Rectangle {
        implicitWidth: 4
        implicitHeight: 4
        radius: 2
        color: root.pressed ? MichiPalette.auroraCyan
            : root.hovered ? MichiPalette.textSecondary : MichiPalette.textMuted
        opacity: root.active || root.hovered ? (root.hovered ? 0.95 : 0.72) : 0
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.standard }
        }
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
    }
    background: Item { }
}
