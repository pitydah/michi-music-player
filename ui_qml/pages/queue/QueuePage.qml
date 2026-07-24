import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../components/foundations"

Item {
    id: root
    objectName: "queuePage_control"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Cola de reproducción"
    Accessible.description: "Gestiona la cola de reproducción: reproducir, reordenar, quitar y vaciar pistas"

    property var qb: typeof queueBridge !== "undefined" ? queueBridge : null
    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _selectedItems: ""
    property bool _multiSelect: false
    property int pageState: root.qb
                            ? (root.qb.queueCount > 0 ? stateReady : stateEmpty)
                            : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    MichiResponsive { id: responsive; availableWidth: root.width }

    function refresh() {
        if (root.qb) root.qb.refresh()
    }

    function routeEnter(route) {
        root.refresh()
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: qsTr("Cargando cola") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: qsTr("Servicio de cola no disponible") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: MichiBanner { message: qsTr("Cola vacía — agrega canciones para empezar a reproducir"); kind: "info"; dismissible: false }
    }

    RowLayout {
        visible: root.pageState === root.stateReady
        anchors.fill: parent
        anchors.margins: responsive.pageMargin
        spacing: MichiTheme.spacing.lg

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: MichiTheme.spacing.sm

            QueueHeader {
                Layout.fillWidth: true
                qb: root.qb
                notif: root.notif
                nav: root.nav
            }

            QueueActions {
                Layout.fillWidth: true
                qb: root.qb
                ps: root.ps
                notif: root.notif
            }

            QueueListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                qb: root.qb
                ps: root.ps
                nav: root.nav
                notif: root.notif
            }
        }

        Item {
            Layout.fillHeight: true
            Layout.preferredWidth: responsive.medium || responsive.wide ? Math.min(320, root.width * 0.3) : 0
            visible: !responsive.compact
        }
    }

    Component.onCompleted: root.refresh()
}
