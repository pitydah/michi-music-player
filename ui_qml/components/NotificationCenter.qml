import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property var notificationBridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string objectName: "notificationCenter"

    signal dismissAllRequested()

    Accessible.role: Accessible.Panel
    Accessible.name: "Centro de notificaciones"

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            anchors.margins: MichiTheme.spacing.md

            Text {
                text: "Notificaciones"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            MichiButton {
                text: "Descartar todas"
                variant: "ghost"
                visible: root.notificationBridge && (root.notificationBridge.queueLength > 0 || (root.notificationBridge.persistentNotifications && root.notificationBridge.persistentNotifications.length > 0))
                onClicked: {
                    if (root.notificationBridge) root.notificationBridge.clear()
                    root.dismissAllRequested()
                }
            }
        }

        ListView {
            id: notificationList
            width: parent.width
            height: parent.height - 50
            spacing: MichiTheme.spacing.sm
            clip: true
            focus: true
            keyNavigationEnabled: true

            model: root.notificationBridge ? buildModel() : []

            function buildModel() {
                var items = []
                if (root.notificationBridge.persistentNotifications) {
                    for (var i = 0; i < root.notificationBridge.persistentNotifications.length; i++) {
                        var n = root.notificationBridge.persistentNotifications[i]
                        n._section = "Persistentes"
                        items.push(n)
                    }
                }
                if (root.notificationBridge.currentNotification && !root.notificationBridge.currentNotification.persistent) {
                    var c = root.notificationBridge.currentNotification
                    c._section = "Transitorias"
                    items.push(c)
                }
                return items
            }

            section.property: "_section"
            section.criteria: ViewSection.FullString
            section.delegate: Item {
                width: parent.width
                height: 28
                Text {
                    text: section
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: MichiTheme.typography.weightMedium
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.md
                }
            }

            delegate: NotificationItem {
                width: parent.width
                notificationId: modelData.id || ""
                kind: modelData.kind || "info"
                title: modelData.title || ""
                message: modelData.text || ""
                timestamp: modelData.timestamp || 0
                persistent: modelData.persistent || false
                progress: modelData.progress !== undefined ? modelData.progress : -1
                jobId: modelData.job_id || ""
                action: modelData.action || ""

                onDismissRequested: function(id) {
                    if (root.notificationBridge) root.notificationBridge.dismiss(id)
                }
                onActionRequested: function(id) {
                    if (root.notificationBridge) root.notificationBridge.executeNotificationAction(id)
                }
            }

            Text {
                id: emptyText
                anchors.centerIn: parent
                text: "No hay notificaciones"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: notificationList.count === 0
            }
        }
    }
}
