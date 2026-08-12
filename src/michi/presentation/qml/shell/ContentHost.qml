import QtQuick
import QtQuick.Layouts
import "../theme"
import "../views"

Item {
    id: root
    property string currentRoute: ""

    function routeIndex(route) {
        switch (route) {
        case "now_playing": return 0
        case "library":     return 1
        case "queue":       return 2
        case "settings":    return 3
        default:            return 1
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.backgroundBase
    }

    StackLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.space16
        currentIndex: root.routeIndex(root.currentRoute)

        NowPlayingView { }
        LibraryView { }
        QueueView { }
        SettingsPlaceholder { }
    }
}
