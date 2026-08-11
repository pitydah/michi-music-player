import QtQuick
import QtQuick.Layouts

Item {
    id: root

    property string currentRoute: ""

    Rectangle {
        anchors.fill: parent
        color: "#1a1a2e"
    }

    Loader {
        id: contentLoader
        anchors.fill: parent
        anchors.margins: 16
        source: {
            switch (root.currentRoute) {
                case "now_playing": return "../views/NowPlayingView.qml"
                case "library":     return "../views/LibraryView.qml"
                case "queue":       return "../views/QueueView.qml"
                default:            return ""
            }
        }
    }
}
