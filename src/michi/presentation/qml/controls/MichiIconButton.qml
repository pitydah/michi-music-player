import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Button {
    id: root
    property string iconName: "circle"
    property string accessibleName: text
    property bool selected: checked
    implicitWidth: MichiMetrics.controlMedium
    implicitHeight: MichiMetrics.controlMedium
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName

    contentItem: MichiIcon {
        name: root.iconName
        width: MichiMetrics.iconMedium
        height: width
        anchors.centerIn: parent
        iconColor: !root.enabled ? MichiPalette.textDisabled
            : root.selected ? MichiPalette.auroraBlue
            : root.hovered ? MichiPalette.textPrimary : MichiPalette.textSecondary
    }
    background: Rectangle {
        radius: MichiRadius.md
        color: root.pressed ? MichiSemanticColors.surfacePressed
            : root.hovered ? MichiSemanticColors.surfaceHover
            : root.selected ? MichiSemanticColors.surfaceSelected : "transparent"
        border.width: root.selected ? 1 : 0
        border.color: MichiPalette.auroraBlue
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
        MichiFocusRing { visualFocus: root.visualFocus }
    }
    MichiTooltip {
        visible: root.hovered && root.accessibleName.length > 0
        text: root.accessibleName
    }
}
