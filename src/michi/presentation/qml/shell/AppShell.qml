import QtQuick
import QtQuick.Layouts
import "../patterns"
import "../theme"
import "../views"

Item {
    id: root
    property string currentRoute: ""
    property bool searchOpened: false
    property string lastContentRoute: "library"
    signal navigationRequested(string routeId)

    onCurrentRouteChanged: {
        if (currentRoute !== "queue" && currentRoute !== "")
            lastContentRoute = currentRoute
    }

    Rectangle { anchors.fill: parent; color: MichiSemanticColors.backplane }

    RowLayout {
        anchors.fill: parent
        anchors.margins: MichiMetrics.islandGap
        spacing: MichiMetrics.islandGap

        Sidebar {
            Layout.preferredWidth: compact ? MichiMetrics.sidebarCompact : MichiMetrics.sidebarExpanded
            Layout.fillHeight: true
            compact: MichiBreakpoints.isCompact(root.width)
            currentRoute: root.currentRoute
            onNavigationRequested: routeId => root.navigationRequested(routeId)
        }

        ContentHost {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentRoute: root.currentRoute === "queue" ? root.lastContentRoute : root.currentRoute
        }
    }

    Loader {
        anchors.fill: parent
        z: 80
        active: root.currentRoute === "queue"
        visible: active
        sourceComponent: queueDrawerComponent
    }

    Component {
        id: queueDrawerComponent
        QueueView {
            onCloseRequested: root.navigationRequested(root.lastContentRoute)
        }
    }

    SearchOverlay {
        anchors.fill: parent
        z: 100
        opened: root.searchOpened
        onCloseRequested: root.searchOpened = false
        onNavigationRequested: routeId => root.navigationRequested(routeId)
    }

    function openSearch() { searchOpened = true }
    function goBack() {
        if (searchOpened) {
            searchOpened = false
            return
        }
        if (currentRoute === "queue") {
            navigationRequested(lastContentRoute)
            return
        }
        navigationRequested("library")
    }
}
