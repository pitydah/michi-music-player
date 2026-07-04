import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property var registry: typeof routeRegistryBridge !== "undefined" ? routeRegistryBridge : null
    property string currentRoute: "home"
    property string lastError: ""
    property string lastLoadedRoute: ""
    property bool loading: false

    function loadRoute(route) {
        currentRoute = route
        var source = registry ? registry.getSource(route) : getFallbackSource(route)
        if (!source) source = "../pages/PlaceholderPage.qml"
        lastError = ""
        loading = true
        pageLoader.source = ""
        pageLoader.source = source
    }

    function getFallbackSource(route) {
        var sources = {
            "home": "../pages/home/HomePage.qml",
            "mix": "../pages/MixHubPage.qml",
            "connections": "../pages/connections/ConnectionsPage.qml",
            "home_audio": "../pages/home_audio/HomeAudioPage.qml",
            "assistant": "../pages/assistant/AssistantPage.qml",
            "library": "../pages/library/LibraryPage.qml",
            "audio_lab": "../pages/assistant/AudioLabPage.qml",
            "radio": "../pages/RadioPage.qml",
            "playlists": "../pages/playlists/PlaylistsPage.qml",
            "playlist_detail": "../pages/playlists/PlaylistDetailPage.qml",
            "metadata_inspector": "../pages/metadata/MetadataInspectorPage.qml",
            "mix_detail": "../pages/MixDetailPage.qml",
            "playback": "../pages/PlaybackPage.qml",
            "settings": "../pages/SettingsPage.qml",
            "devices": "../pages/DevicesPage.qml",
            "eq": "../pages/EqPage.qml",
            "library_doctor": "../pages/LibraryDoctorPage.qml",
            "disc_lab": "../pages/DiscLabPage.qml",
            "output_profiles": "../pages/OutputProfilesPage.qml",
            "smart_tagging": "../pages/SmartTaggingPage.qml",
            "diagnostics": "../pages/DiagnosticsPage.qml",
        }
        return sources[route] || "../pages/PlaceholderPage.qml"
    }

    function callOnPage(methodName, arg) {
        if (pageLoader.item && typeof pageLoader.item[methodName] === "function") {
            pageLoader.item[methodName](arg)
        }
    }

    onCurrentRouteChanged: {
        callOnPage("routeEnter", currentRoute)
    }

    Loader {
        id: pageLoader
        anchors.fill: parent
        asynchronous: true
        source: ""

        opacity: status === Loader.Ready ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: MichiTheme.motion.fast; easing.type: Easing.OutCubic } }

        onStatusChanged: {
            if (status === Loader.Ready) {
                loading = false
                lastLoadedRoute = currentRoute
                callOnPage("routeEnter", currentRoute)
            } else if (status === Loader.Error) {
                loading = false
                lastError = "Failed to load: " + source
                console.warn("[PageStack] Failed to load:", source)
                source = "../pages/PlaceholderPage.qml"
            } else if (status === Loader.Loading) {
                loading = true
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: pageLoader.status === Loader.Null && currentRoute !== "" && !loading
        z: -1
    }
}
