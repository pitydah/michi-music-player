import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Queue List View"
    objectName: "queueListView_control"
    focus: true
    property var qb: null
    property var ps: null
    property var nav: null
    property var notif: null
    property int _dragFrom: -1

    ListView {
        id: queueList
        anchors.fill: parent
        model: root.qb ? root.qb.queueModel : null
        clip: true
        spacing: 2
        boundsBehavior: Flickable.StopAtBounds
        focusPolicy: Qt.StrongFocus

        delegate: Item {
            width: queueList.width
            height: 48

            DragHandler {
                id: dragHandler
                target: null
                onActiveChanged: {
                    if (active) {
                        root._dragFrom = index
                    }
                }
            }

            QueueItem {
                width: parent.width
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
        }

        DropArea {
            anchors.fill: parent
            onDropped: function(drop) {
                if (root._dragFrom >= 0 && root.qb && root.qb.moveItem) {
                    var toIndex = queueList.indexAt(0, drop.y)
                    if (toIndex >= 0 && toIndex !== root._dragFrom) {
                        root.qb.moveItem(root._dragFrom, toIndex)
                    }
                }
                root._dragFrom = -1
            }
        }

        QueueEmptyState {
            anchors.centerIn: parent
            visible: queueList.count === 0
        }
    }
}
