import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Button {
    id: root
    property string variant: "primary"
    property string iconName: ""
    property string accessibleName: text
    property bool iconOnly: false
    property bool selected: checked
    property real iconSize: MichiMetrics.iconSmall
    property real iconStrokeWidth: 1.7
    readonly property bool primary: variant === "primary"
    readonly property bool ghost: variant === "ghost"
    readonly property bool danger: variant === "danger"

    implicitHeight: MichiMetrics.controlMedium
    implicitWidth: iconOnly ? implicitHeight
        : Math.max(72, contentRow.implicitWidth + MichiSpacing.xl * 2)
    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.md
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName

    contentItem: Row {
        id: contentRow
        spacing: MichiSpacing.sm
        anchors.centerIn: parent
        MichiIcon {
            visible: root.iconName !== ""
            name: root.iconName
            width: root.iconSize
            height: width
            strokeWidth: root.iconStrokeWidth
            iconColor: label.color
            anchors.verticalCenter: parent.verticalCenter
        }
        MichiText {
            id: label
            text: root.text
            visible: !root.iconOnly && text.length > 0
            role: "secondary"
            color: !root.enabled ? MichiPalette.textDisabled
                : root.danger ? MichiPalette.error
                : root.primary ? MichiPalette.obsidian
                : root.selected || root.hovered ? MichiPalette.textPrimary
                : MichiPalette.textSecondary
            font.weight: root.primary || root.selected ? Font.DemiBold : Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    background: Rectangle {
        id: buttonSurface
        radius: MichiRadius.md
        color: !root.enabled ? MichiPalette.graphite
            : root.danger ? (root.hovered ? MichiSemanticColors.surfaceHover : MichiSemanticColors.controlSurface)
            : root.primary ? (root.pressed ? MichiSemanticColors.auroraPressed
                : root.hovered ? MichiSemanticColors.auroraHover : MichiPalette.auroraBlue)
            : root.pressed ? MichiSemanticColors.surfacePressed
            : root.hovered ? MichiSemanticColors.surfaceHover
            : root.selected ? MichiSemanticColors.surfaceSelected
            : root.ghost ? "transparent" : MichiPalette.smoke
        border.width: root.danger ? 1 : root.primary ? 0 : 1
        border.color: root.danger ? MichiPalette.error
            : root.selected ? MichiPalette.auroraBlue
            : root.hovered ? MichiSemanticColors.borderStrong
            : MichiSemanticColors.borderSubtle
        y: root.pressed ? 1 : 0
        scale: root.pressed ? 0.985 : root.hovered ? 1.01 : 1

        Rectangle {
            visible: root.enabled && root.primary
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: parent.radius
            anchors.rightMargin: parent.radius
            height: 1
            color: root.primary ? MichiSemanticColors.innerHighlightStrong
                : MichiPalette.auroraCyan
            opacity: root.pressed ? 0.18 : 0.55
        }
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
        Behavior on y {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.instant }
        }
        Behavior on scale {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
        }
        MichiFocusRing { visualFocus: root.visualFocus }
    }
    MichiTooltip {
        visible: root.iconOnly && root.hovered && root.accessibleName.length > 0
        text: root.accessibleName
    }
}
