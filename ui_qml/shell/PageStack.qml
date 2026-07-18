import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Stack"
    objectName: "pageStack"
    focus: true
    id: root

    property var registry: typeof routeRegistryBridge !== "undefined" ? routeRegistryBridge : null
    property string currentRoute: "home"
    property string lastError: ""
    property string lastLoadedRoute: ""
    property bool loading: false
    property string _prevRoute: ""

    function loadRoute(route) {
        var source = registry ? registry.getSource(route) : getFallbackSource(route)
        if (!source) source = "../pages/PlaceholderPage.qml"
        _prevRoute = currentRoute
        currentRoute = route
        lastError = ""
        loading = true
        callOnPage("routeLeave", _prevRoute)
        pageLoader.source = ""
        pageLoader.source = source
    }

    function getFallbackSource(route) {
        var sources = {
            "home": "../pages/home/HomePage.qml",
            "lyrics": "../pages/lyrics/LyricsPage.qml",
            "mix": "../pages/mix/MixHubPage.qml",
            "connections": "../pages/connections/ConnectionsPage.qml",
            "album_detail": "../pages/library/AlbumDetailPage.qml",
            "artist_detail": "../pages/library/ArtistDetailPage.qml",
            "home_audio": "../pages/home_audio/HomeAudioPage.qml",
            "assistant": "../pages/assistant/AssistantPage.qml",
            "ai.settings": "../pages/assistant/AISettingsPage.qml",
            "library": "../pages/library/LibraryPage.qml",
            "audio_lab": "../pages/audio_lab/AudioLabOverviewPage.qml",
            "audio_lab.analysis": "../pages/audio_lab/AudioAnalysisPage.qml",
            "audio_lab.conversion": "../pages/audio_lab/AudioConversionPage.qml",
            "audio_lab.normalization": "../pages/audio_lab/AudioNormalizationPage.qml",
            "audio_lab.replaygain": "../pages/audio_lab/ReplayGainPage.qml",
            "audio_lab.integrity": "../pages/audio_lab/AudioIntegrityPage.qml",
            "audio_lab.comparison": "../pages/audio_lab/AudioComparisonPage.qml",
            "audio_lab.jobs": "../pages/audio_lab/AudioBatchJobsPage.qml",
            "audio_lab.profiles": "../pages/audio_lab/AudioConversionProfileEditor.qml",
            "audio_lab.cd_ripper": "../pages/audio_lab/CDRipperPage.qml",
            "audio_lab.adc_recorder": "../pages/audio_lab/ADCRecorderPage.qml",
            "audio_lab.diagnostics": "../pages/audio_lab/hubs/DiagnosticsHubPage.qml",
            "audio_lab.identifier": "../pages/audio_lab/hubs/IdentifierHubPage.qml",
            "audio_lab.backup": "../pages/audio_lab/hubs/BackupHubPage.qml",
            "audio_lab.output_profiles": "../pages/audio_lab/hubs/OutputProfilesHubPage.qml",
            "audio_lab.local_intelligence": "../pages/audio_lab/hubs/LocalIntelligenceHubPage.qml",
            "radio": "../pages/radio/RadioPage.qml",
            "group_editor": "../pages/home_audio/GroupEditorPage.qml",
            "playlists": "../pages/playlists/PlaylistsPage.qml",
            "playlist_detail": "../pages/playlists/PlaylistDetailPage.qml",
            "smart_playlist_editor": "../pages/playlists/SmartPlaylistEditorPage.qml",
            "metadata_inspector": "../pages/metadata/MetadataInspectorPage.qml",
            "metadata_editor": "../pages/metadata/MetadataEditorPage.qml",
            "metadata_single": "../pages/metadata/MetadataSingleEditor.qml",
            "metadata_batch": "../pages/metadata/MetadataBatchEditor.qml",
            "mix_detail": "../pages/mix/MixDetailPage.qml",
            "mix_generator": "../pages/mix/MixGeneratorPage.qml",
            "mix_result": "../pages/mix/MixResultPage.qml",
            "mix_rule_editor": "../pages/mix/MixRuleEditorPage.qml",
            "playback": "../pages/PlaybackPage.qml",
            "settings": "../pages/SettingsPage.qml",
            "devices": "../pages/devices/DevicesPage.qml",
            "eq": "../pages/EqPage.qml",
            "library_doctor": "../pages/library_doctor/LibraryDoctorPage.qml",
            "disc_lab": "../pages/disc_lab/DiscLabPage.qml",
            "output_profiles": "../pages/outputs/OutputProfilesPage.qml",
            "smart_tagging": "../pages/SmartTaggingPage.qml",
            "diagnostics": "../pages/DiagnosticsPage.qml",
            "devices.profile_editor": "../pages/devices/DeviceSyncProfileEditor.qml",
            "zone_detail": "../pages/home_audio/ZoneDetailPage.qml",
            "stream_routing": "../pages/home_audio/StreamRoutingPage.qml",
            "latency": "../pages/home_audio/LatencyPage.qml",
        }
        return sources[route] || "../pages/PlaceholderPage.qml"
    }

    function getRouteTitle(route) {
        var titles = {
            "home": "Inicio",
            "library": "Biblioteca",
            "mix": "Mix",
            "playback": "Reproducción",
            "nowplaying": "Reproduciendo",
            "queue": "Cola",
            "playlists": "Playlists",
            "playlist_detail": "Detalle de lista",
            "history": "Historial",
            "radio": "Radio",
            "connections": "Conexiones",
            "home_audio": "Audio del Hogar",
            "devices": "Dispositivos",
            "settings": "Ajustes",
            "eq": "Ecualizador",
            "diagnostics": "Diagnóstico",
            "assistant": "Michi IA",
            "audio_lab": "Audio Lab",
            "audio_lab.analysis": "Análisis Técnico",
            "audio_lab.conversion": "Conversión",
            "audio_lab.normalization": "Normalización",
            "audio_lab.replaygain": "ReplayGain",
            "audio_lab.integrity": "Integridad",
            "audio_lab.comparison": "Comparación",
            "audio_lab.jobs": "Trabajos",
            "audio_lab.profiles": "Perfiles",
            "audio_lab.cd_ripper": "Ripeo de CD",
            "audio_lab.adc_recorder": "Grabación ADC",
            "audio_lab.diagnostics": "Diagnóstico de Audio",
            "audio_lab.identifier": "Identificador",
            "audio_lab.backup": "Respaldar",
            "audio_lab.output_profiles": "Perfiles de Salida",
            "audio_lab.local_intelligence": "Inteligencia Local",
            "library_doctor": "Library Doctor",
            "disc_lab": "Disc Lab",
            "output_profiles": "Perfiles de salida",
            "smart_tagging": "Smart Tagging",
            "smart_playlist_editor": "Smart Playlist",
            "metadata_inspector": "Inspector de metadatos",
            "metadata_editor": "Editor de metadatos",
            "metadata_single": "Editar metadatos",
            "metadata_batch": "Edición por lotes",
            "group_editor": "Editor de grupos",
            "mix_detail": "Detalle de Mix",
            "mix_generator": "Generar Mix",
            "mix_result": "Resultado Mix",
            "mix_rule_editor": "Reglas de Mix",
            "album_detail": "Álbum",
            "artist_detail": "Artista",
            "zone_detail": "Detalle de Zona",
            "stream_routing": "Enrutamiento",
            "latency": "Latencia",
        }
        return titles[route] || "Michi Music Player"
    }

    function callOnPage(methodName, arg) {
        if (pageLoader.item && typeof pageLoader.item[methodName] === "function") {
            pageLoader.item[methodName](arg)
        }
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteRefreshRequested(route) {
            callOnPage("routeRefresh", route)
        }
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

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: lastError !== ""
        z: 100

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md
            width: Math.min(400, parent.width * 0.8)

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Error de ruta"
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Text {
                width: parent.width
                text: root.lastError
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Ir a Inicio"
                variant: "primary"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home")
                    root.lastError = ""
                }
            }
        }
    }
}
