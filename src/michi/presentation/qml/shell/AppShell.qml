import QtQuick
import QtQuick.Layouts
import "../shell"

RowLayout {
    id: root
    anchors.fill: parent
    spacing: 0

    property string currentRoute: ""

    signal navigationRequested(string routeId)

    Sidebar {
        Layout.preferredWidth: 180
        Layout.fillHeight: true
        currentRoute: root.currentRoute
        onNavigationRequested: routeId => root.navigationRequested(routeId)
    }

    ContentHost {
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentRoute: root.currentRoute
    }
}
