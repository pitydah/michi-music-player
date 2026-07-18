import QtQuick
import "../theme"

// @deprecated Use StatusBadge instead — MichiBadge is unused in pages/.
// StatusBadge offers more kind variants (experimental, disconnected, active)
// and is used across 100+ locations in pages/.
Rectangle {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string badgeText: ""
    property string variant: "info"
    property int badgeSize: MichiTheme.typography.badgeSize
    property string accessibleName: ""
    property string accessibleDescription: ""

    height: 20
    width: textItem.width + MichiTheme.spacing.sm * 2
    radius: MichiTheme.radius.pill

    Accessible.role: Accessible.StatusBar
    Accessible.name: root.accessibleName !== "" ? root.accessibleName : root.badgeText
    Accessible.description: root.accessibleDescription

    color: {
        switch (root.variant) {
            case "success": return MichiTheme.colors.badgeActiveBg
            case "warning": return MichiTheme.colors.badgeWarningBg
            case "error":
            case "danger": return MichiTheme.colors.badgeDangerBg
            case "neutral": return MichiTheme.colors.badgeMutedBg
            default: return MichiTheme.colors.badgeInfoBg
        }
    }

    border.width: 0

    Text {
        id: textItem
        anchors.centerIn: parent
        text: root.badgeText
        font.pixelSize: root.badgeSize
        font.weight: MichiTheme.typography.weightMedium
        color: {
            switch (root.variant) {
                case "success": return MichiTheme.colors.badgeActiveText
                case "warning": return MichiTheme.colors.warning
                case "error":
                case "danger": return MichiTheme.colors.error
                case "neutral": return MichiTheme.colors.textMuted
                default: return MichiTheme.colors.badgeInfoText
            }
        }
    }
}
