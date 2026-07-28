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
    readonly property string semanticVariant: {
        switch (root.variant.toLowerCase()) {
        case "success":
        case "succeeded":
        case "completed": return "success"
        case "warning":
        case "experimental": return "warning"
        case "error":
        case "danger":
        case "failed":
        case "disconnected": return "error"
        default: return "info"
        }
    }
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
        switch (root.semanticVariant) {
            case "success": return MichiTheme.colors.badgeActiveBg
            case "warning": return MichiTheme.colors.badgeWarningBg
            case "error": return MichiTheme.colors.badgeDangerBg
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
            switch (root.semanticVariant) {
                case "success": return MichiTheme.colors.badgeActiveText
                case "warning": return MichiTheme.colors.warning
                case "error": return MichiTheme.colors.error
                default: return MichiTheme.colors.badgeInfoText
            }
        }
    }
}
