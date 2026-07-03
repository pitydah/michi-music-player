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
            case "radio": return "../pages/RadioPage.qml"
            case "playlists": return "../pages/playlists/PlaylistsPage.qml"
            case "playlist_detail": return "../pages/playlists/PlaylistDetailPage.qml"
            case "metadata_inspector": return "../pages/metadata/MetadataInspectorPage.qml"
            case "mix_detail": return "../pages/MixDetailPage.qml"
            case "playback": return "../pages/PlaybackPage.qml"
            case "settings": return "../pages/SettingsPage.qml"
            case "devices": return "../pages/DevicesPage.qml"
            case "eq": return "../pages/EqPage.qml"
            case "library_doctor": return "../pages/LibraryDoctorPage.qml"
            case "disc_lab": return "../pages/DiscLabPage.qml"
            case "output_profiles": return "../pages/OutputProfilesPage.qml"
            case "smart_tagging": return "../pages/SmartTaggingPage.qml"
            default: return "../pages/PlaceholderPage.qml"
        }
    }

    Loader {
        id: pageLoader
        anchors.fill: parent
        asynchronous: true
        source: getSource(currentRoute)

        opacity: status === Loader.Ready ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: MichiTheme.motion.fast; easing.type: Easing.OutCubic } }

        onStatusChanged: {
            if (status === Loader.Error) {
                console.warn("[PageStack] Failed to load:", source)
                source = "../pages/PlaceholderPage.qml"
            }
        }
    }
}
