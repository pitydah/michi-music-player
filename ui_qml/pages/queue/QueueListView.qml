import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Queue List View"
    objectName: "queueListView"
    focus: true
    property var qb: null
    property var ps: null
    property var nav: null
    property var notif: null

    ListView {
        id: queueList
        anchors.fill: parent
        model: root.qb ? root.qb.queueModel : null
        clip: true
        spacing: 2
        boundsBehavior: Flickable.StopAtBounds

        delegate: QueueItem {
            width: queueList.width
            height: 48
            qb: root.qb
            ps: root.ps
            notif: root.notif
            itemIndex: index
            itemTitle: model.title || ""
            itemArtist: model.artist || ""
            itemAlbum: model.album || ""
            itemDuration: model.duration || 0
            itemIsCurrent: model.current || false
        }

        QueueEmptyState {
            anchors.centerIn: parent
            visible: queueList.count === 0
        }
    }
}
