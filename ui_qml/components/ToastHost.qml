import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Toast Host"
    objectName: "toastHost"
    focus: true
    id: root

    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: MichiTheme.spacing.xxl
        width: Math.min(400, parent.width * 0.8)
        height: 48
        radius: MichiTheme.radius.sm
        visible: root.notif ? (root.notif.visible || false) : false

        color: {
            if (!root.notif || !root.notif.kind) return "transparent"
            switch (root.notif.kind) {
                case "success": return MichiTheme.colors.badgeActiveBg
                case "warning": return MichiTheme.colors.badgeWarningBg
                case "error": return MichiTheme.colors.badgeDangerBg
                default: return MichiTheme.colors.badgeInfoBg
            }
        }

        border.color: {
            if (!root.notif || !root.notif.kind) return "transparent"
            switch (root.notif.kind) {
                case "success": return MichiTheme.colors.success
                case "warning": return MichiTheme.colors.warning
                case "error": return MichiTheme.colors.error
                default: return MichiTheme.colors.accentBlue
            }
        }
        border.width: 1

        Text {
            anchors.left: parent.left
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.verticalCenter: parent.verticalCenter
            text: root.notif ? (root.notif.message || "") : ""
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            elide: Text.ElideRight
            width: parent.width - 60
        }

        MichiIconButton {
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.spacing.xs
            anchors.verticalCenter: parent.verticalCenter
            iconSource: "qrc:/icons/nav_back.svg"
            btnSize: 28
            tooltipText: "Cerrar"
            onClicked: { if (root.notif) root.notif.clear() }
        }

        Timer {
            interval: 4000
            running: root.notif ? (root.notif.visible || false) : false
            onTriggered: { if (root.notif) root.notif.clear() }
        }
    }
}
