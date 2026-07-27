import QtQuick
import "../theme"

Rectangle {
    Accessible.role: Accessible.Indicator
    Accessible.name: root.text
    objectName: "statusBadge"
    id: root

    property string text: ""
    property string kind: "info"
    property bool pulse: false

    property int maximumWidth: 200

    implicitHeight: 24
    implicitWidth: Math.min(text !== "" ? badgeRow.implicitWidth + MichiTheme.spacing.md * 2 : 24,
                            root.maximumWidth)
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

    Row {
        id: badgeRow
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.xs

        readonly property color statusColor: {
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

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 6
            height: 6
            radius: 3
            color: badgeRow.statusColor
        }

        Text {
            id: txt
            text: root.text
            color: badgeRow.statusColor
            font.pixelSize: MichiTheme.typography.badgeSize
            font.weight: MichiTheme.typography.weightMedium
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }
}
