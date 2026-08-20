import QtQuick
import QtQuick.Layouts
import "../patterns"
import "../theme"

Item {
    id: root
    property string currentRoute: ""
    property bool searchOpened: false
    signal navigationRequested(string routeId)

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
            currentRoute: root.currentRoute
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
}
