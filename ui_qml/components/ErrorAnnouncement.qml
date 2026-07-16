import QtQuick
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Error Announcement"
    objectName: "errorAnnouncement"
    focus: true
    id: root

    property string errorTitle: ""
    property string errorDetail: ""
    property bool active: false

    signal announcementFinished()


    Accessible.description: root.errorDetail

    visible: false

    onErrorTitleChanged: {
        if (root.errorTitle !== "") {
            root.active = true
            root.visible = true
            Accessible.name = root.errorTitle
            Accessible.description = root.errorDetail
            errorTimer.restart()
        }
    }

    Timer {
        id: errorTimer
        interval: 200
        onTriggered: {
            root.visible = false
            root.active = false
            root.announcementFinished()
        }
    }
}
