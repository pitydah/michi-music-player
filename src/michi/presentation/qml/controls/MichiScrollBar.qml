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
        color: root.pressed ? MichiPalette.auroraBlue : MichiPalette.textMuted
        opacity: root.active ? 0.8 : 0
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.standard }
        }
    }
    background: Item { }
}
