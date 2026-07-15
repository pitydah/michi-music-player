import QtQuick
import "../theme"
import "."

Item {
    id: root

    property string errorTitle: ""
    property string errorDetail: ""
    property bool active: false

    signal announcementFinished()

    objectName: "errorAnnouncement"

    Accessible.role: Accessible.Alert
    Accessible.name: root.errorTitle
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
