import QtQuick
import QtQuick.Controls
import "../theme"
import "."

Item {
    id: root

    property string message: ""
    property string messageKind: "info"
    property bool active: false

    signal announcementFinished()

    objectName: "notificationAnnouncement"

    Accessible.role: Accessible.Alert
    Accessible.name: root.message
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
