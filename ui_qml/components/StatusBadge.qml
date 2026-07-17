import QtQuick
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Status Badge"
    objectName: "statusBadge"
    focus: true
    id: root

    property string text: ""
    property string kind: "info"
    property bool pulse: false

    implicitHeight: 22
    implicitWidth: text !== "" ? txt.implicitWidth + MichiTheme.spacing.md * 2 : 22
    radius: MichiTheme.radius.pill

    color: {
        switch (root.kind) {
            case "success": return MichiTheme.colors.badgeActiveBg
            case "warning": return MichiTheme.colors.badgeWarningBg
            case "error": return MichiTheme.colors.badgeDangerBg
            case "experimental": return MichiTheme.colors.badgeExperimentalBg
            case "disconnected": return MichiTheme.colors.badgeMutedBg
            case "active": return MichiTheme.colors.badgeActiveBg
            default: return MichiTheme.colors.badgeInfoBg
        }
    }

    border.color: MichiTheme.colors.borderInner
    border.width: MichiTheme.borderWidth

    Text {
        id: txt
        anchors.centerIn: parent
        text: root.text
        color: {
            switch (root.kind) {
                case "success": return MichiTheme.colors.success
                case "warning": return MichiTheme.colors.warning
                case "error": return MichiTheme.colors.error
                case "experimental": return MichiTheme.colors.experimental
                case "disconnected": return MichiTheme.colors.disconnected
                case "active": return MichiTheme.colors.success
                default: return MichiTheme.colors.accentBlue
            }
        }
        font.pixelSize: MichiTheme.typography.badgeSize
        font.weight: MichiTheme.typography.weightMedium
        visible: text !== ""
    }
}
