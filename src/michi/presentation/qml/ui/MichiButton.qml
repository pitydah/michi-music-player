import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: root

    property string variant: "primary"

    implicitHeight: MichiTheme.controlHeightMedium
    leftPadding: MichiTheme.space16
    rightPadding: MichiTheme.space16

    font.pixelSize: MichiTheme.fontSizeBody
    font.weight: MichiTheme.fontWeightMedium

    contentItem: Text {
        text: root.text
        font: root.font
        color: {
            if (!root.enabled) return MichiTheme.textDisabled
            if (root.variant === "ghost") return root.hovered ? MichiTheme.accentHover : MichiTheme.textSecondary
            return MichiTheme.textPrimary
        }
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: MichiTheme.radiusMedium
        color: {
            if (!root.enabled) return MichiTheme.surfacePrimary
            if (root.pressed) return MichiTheme.accentPressed
            if (root.hovered) return MichiTheme.accentHover
            if (root.variant === "primary") return MichiTheme.accent
            if (root.variant === "secondary") return MichiTheme.surfaceSecondary
            return "transparent"
        }
        border.color: root.variant === "ghost"
            ? (root.hovered ? MichiTheme.accentHover : MichiTheme.borderSubtle)
            : "transparent"
        border.width: root.variant === "ghost" ? 1 : 0
    }
}
