import QtQuick
import QtQuick.Layouts
import "../views"

Item {
    id: root

    property string currentRoute: ""

    function routeIndex(route) {
        switch (route) {
        case "now_playing": return 0
        case "library":     return 1
        case "queue":       return 2
        default:            return 1  // fallback: Library
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#1a1a2e"
    }

    StackLayout {
        anchors.fill: parent
        anchors.margins: 16
        currentIndex: root.routeIndex(root.currentRoute)

        NowPlayingView { }
        LibraryView { }
        QueueView { }
    }
}
