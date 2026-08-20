import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Slider {
    id: root
    property string accessibleName: "Slider"
    implicitHeight: MichiMetrics.controlSmall
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.Slider
    Accessible.name: accessibleName

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        implicitWidth: 200
        implicitHeight: 4
        width: root.availableWidth
        height: implicitHeight
        radius: 2
        color: MichiPalette.smokeRaised
        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: root.enabled ? MichiPalette.auroraBlue : MichiPalette.textDisabled
        }
    }
    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        implicitWidth: 14
        implicitHeight: 14
        radius: width / 2
        color: root.enabled ? MichiPalette.textPrimary : MichiPalette.textDisabled
        border.width: 2
        border.color: root.pressed || root.visualFocus
            ? MichiPalette.auroraBlue : MichiSemanticColors.borderStrong
        scale: root.pressed ? 1.08 : 1
        Behavior on scale {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.micro }
        }
        MichiFocusRing { visualFocus: root.visualFocus }
    }
}
