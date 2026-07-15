import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Item {
    id: root

    property var qb: typeof queueBridge !== "undefined" ? queueBridge : null
    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge
                   : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _selectedItems: ""
    property bool _multiSelect: false

    objectName: "queue.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Cola de reproducción"
    Accessible.description: "Gestión de la cola de reproducción"

    Keys.onEscapePressed: {
        root._selectedItems = ""
        root._multiSelect = false
    }

    function refresh() {
        if (root.qb) root.qb.refresh()
    }

    function routeEnter(route) {
        root.refresh()
    }

    ColumnLayout {
        id: mainLayout
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.md
        objectName: "queue.mainLayout"

        QueueHeader {
            id: queueHeader
            Layout.fillWidth: true
            qb: root.qb
            notif: root.notif
            nav: root.nav
        }

        QueueActions {
            id: queueActions
            Layout.fillWidth: true
            qb: root.qb
            ps: root.ps
            notif: root.notif
        }

        QueueListView {
            id: queueListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            qb: root.qb
            ps: root.ps
            nav: root.nav
            notif: root.notif
        }
    }

    Component.onCompleted: root.refresh()
}
