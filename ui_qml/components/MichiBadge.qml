import QtQuick
import "../theme"

Rectangle {
    id: root

    property string badgeText: ""
    property string variant: "info"
    property int badgeSize: MichiTheme.typography.badgeSize

    height: 20
    width: textItem.width + MichiTheme.spacing.sm * 2
    radius: MichiTheme.radiusPill

    color: {
        switch (root.variant) {
            case "success": return MichiTheme.colors.badgeActiveBg
            case "warning": return MichiTheme.colors.badgeWarningBg
            case "danger": return MichiTheme.colors.badgeDangerBg
            case "experimental": return MichiTheme.colors.badgeExperimentalBg
            case "muted": return MichiTheme.colors.badgeMutedBg
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
                case "danger": return MichiTheme.colors.error
                case "experimental": return MichiTheme.colors.badgeExperimentalText
                case "muted": return MichiTheme.colors.textMuted
                default: return MichiTheme.colors.badgeInfoText
            }
        }
    }
}
