import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string currentRoute: "home"

    function loadRoute(route) {
        currentRoute = route
        pageLoader.source = ""
        pageLoader.source = getSource(route)
    }

    function getSource(route) {
        switch (route) {
            case "home": return "../pages/home/HomePage.qml"
            case "connections": return "../pages/connections/ConnectionsPage.qml"
            case "home_audio": return "../pages/home_audio/HomeAudioPage.qml"
            case "assistant": return "../pages/assistant/AssistantPage.qml"
            case "library": return "../pages/library/LibraryPage.qml"
            case "audio_lab": return "../pages/assistant/AudioLabPage.qml"
            case "radio": return "../pages/PlaceholderPage.qml"
            case "playlists": return "../pages/PlaceholderPage.qml"
            case "nowplaying": return "../pages/NowPlayingPage.qml"
            default: return "../pages/PlaceholderPage.qml"
        }
    }

    Loader {
        id: pageLoader
        anchors.fill: parent
        asynchronous: true
        source: getSource(currentRoute)

        onStatusChanged: {
            if (status === Loader.Error) {
                console.warn("[PageStack] Failed to load:", source)
                source = "../pages/PlaceholderPage.qml"
            }
        }
    }
}
