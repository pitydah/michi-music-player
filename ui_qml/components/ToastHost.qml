import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 80
        width: Math.min(400, parent.width * 0.8)
        height: 48
        radius: MichiTheme.radiusSm
        visible: root.notif ? root.notif.visible : false

        color: {
            if (!root.notif) return "transparent"
            switch (root.notif.kind) {
                case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.20)
                case "warning": return Qt.rgba(1, 0.75, 0.14, 0.20)
                case "error": return Qt.rgba(1, 0.44, 0.44, 0.20)
                default: return Qt.rgba(0.561, 0.718, 1.0, 0.15)
            }
        }

        border.color: {
            if (!root.notif) return "transparent"
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
            text: root.notif ? root.notif.message : ""
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            elide: Text.ElideRight
            width: parent.width - 60
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.spacing.sm
            anchors.verticalCenter: parent.verticalCenter
            text: "[X]"
            color: MichiTheme.colors.textMuted
            font.pixelSize: 14

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: { if (root.notif) root.notif.clear() }
            }
        }

        Timer {
            interval: 4000
            running: root.notif ? root.notif.visible : false
            onTriggered: { if (root.notif) root.notif.clear() }
        }
    }
}
