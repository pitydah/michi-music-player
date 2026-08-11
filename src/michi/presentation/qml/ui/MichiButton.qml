import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: root

    property string variant: "primary"
    readonly property bool _isPrimary: variant === "primary"
    readonly property bool _isSecondary: variant === "secondary"
    readonly property bool _isGhost: variant === "ghost"

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
            if (root._isPrimary || root._isSecondary) return MichiTheme.textPrimary
            if (root._isGhost) return root.hovered || root.checked
                ? MichiTheme.textPrimary : MichiTheme.textSecondary
            return MichiTheme.textPrimary
        }
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: MichiTheme.radiusMedium

        readonly property color _bg: {
            if (!root.enabled) return MichiTheme.surfacePrimary
            if (root._isGhost) {
                if (root.pressed || root.checked) return MichiTheme.surfaceSelected
                if (root.hovered) return MichiTheme.surfaceHover
                return "transparent"
            }
            if (root._isSecondary) {
                if (root.pressed) return MichiTheme.surfacePressed
                if (root.hovered) return MichiTheme.surfaceHover
                return MichiTheme.surfaceSecondary
            }
            // primary
            if (root.pressed) return MichiTheme.accentPressed
            if (root.hovered) return MichiTheme.accentHover
            return MichiTheme.accent
        }

        color: _bg

        border.color: root.visualFocus ? MichiTheme.accent
            : (root._isGhost && (root.hovered || root.checked))
                ? MichiTheme.accentHover
            : root._isGhost ? MichiTheme.borderSubtle
            : "transparent"
        border.width: root._isGhost || root.visualFocus ? 1 : 0
    }
}
