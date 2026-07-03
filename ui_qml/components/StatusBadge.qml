import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property string kind: "info"
    property bool pulse: false

    implicitHeight: 22
    implicitWidth: text !== "" ? txt.implicitWidth + MichiTheme.spacing.md * 2 : 22
    radius: MichiTheme.radiusPill

    color: {
        switch (root.kind) {
            case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.15)
            case "warning": return Qt.rgba(0.98, 0.75, 0.14, 0.15)
            case "error": return Qt.rgba(0.95, 0.25, 0.25, 0.15)
            case "experimental": return Qt.rgba(0.655, 0.545, 0.980, 0.15)
            case "disconnected": return Qt.rgba(0.42, 0.44, 0.50, 0.15)
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
