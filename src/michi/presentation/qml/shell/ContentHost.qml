import QtQuick
import QtQuick.Layouts
import "../primitives"
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

    MichiSurface { anchors.fill: parent; level: "content"; radius: MichiRadius.floating }

    StackLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        currentIndex: root.routeIndex(root.currentRoute)

        NowPlayingView { }
        LibraryView { }
        QueueView { }
        SettingsView { }
    }
}
