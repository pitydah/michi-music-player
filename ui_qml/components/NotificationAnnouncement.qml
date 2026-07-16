import QtQuick
import QtQuick.Controls
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Notification Announcement"
    objectName: "notificationAnnouncement"
    focus: true
    id: root

    property string message: ""
    property string messageKind: "info"
    property bool active: false

    signal announcementFinished()


    Accessible.description: "Notificación: " + root.message

    visible: false

    onMessageChanged: {
        if (root.message !== "") {
            root.active = true
            root.visible = true
            Accessible.name = root.message
            accessibleTimer.restart()
        }
    }

    Timer {
        id: accessibleTimer
        interval: 100
        onTriggered: {
            root.visible = false
            root.active = false
            root.announcementFinished()
        }
    }

    Text {
        id: messageText
        text: root.message
        color: root.messageKind === "error" ? MichiTheme.colors.error
             : root.messageKind === "success" ? MichiTheme.colors.success
             : root.messageKind === "warning" ? MichiTheme.colors.warning
             : MichiTheme.colors.textPrimary
        font.pixelSize: MichiTheme.typography.bodySize
        visible: false
    }
}
