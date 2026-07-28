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
    readonly property string semanticKind: {
        switch (root.kind.toLowerCase()) {
        case "success":
        case "succeeded":
        case "completed":
        case "done":
        case "connected": return "success"
        case "warning":
        case "degraded":
        case "reconnecting":
        case "experimental": return "warning"
        case "error":
        case "danger":
        case "failed":
        case "failure":
        case "unavailable":
        case "disconnected": return "error"
        default: return "info"
        }
    }

    property int maximumWidth: 200

    implicitHeight: 24
    implicitWidth: Math.min(text !== "" ? badgeRow.implicitWidth + MichiTheme.spacing.md * 2 : 24,
                            root.maximumWidth)
    radius: MichiTheme.radius.pill

    color: {
        switch (root.semanticKind) {
            case "success": return MichiTheme.colors.badgeActiveBg
            case "warning": return MichiTheme.colors.badgeWarningBg
            case "error": return MichiTheme.colors.badgeDangerBg
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
            switch (root.semanticKind) {
            case "success": return MichiTheme.colors.success
            case "warning": return MichiTheme.colors.warning
            case "error": return MichiTheme.colors.error
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
