import QtQuick
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    AlbumBrowseState {
        id: albumBrowseState
        objectName: "albumBrowseState"
    }

    property string currentTab: "songs"
    // M6-PRODUCTION-INTEGRATION: albumMode lives HERE (the root survives
    // the tab recreation) — AlbumsView is recreated on every tab switch and
    // must never be the source of a preference we want to preserve.
    property string albumMode: "grid"
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0
    property var viewPreferences: defaultViewPreferences()

    readonly property var albumModes: [
        "grid", "cover", "vinyl", "timeline", "magazine", "list"
    ]

    function requestAlbumMode(mode) {
        if (albumModes.indexOf(mode) !== -1) {
            albumMode = mode
            root.updateCommonPreference("activeMode", mode)
            root.applyViewPreferences(root.viewPreferences)
        }
    }

    // PR #231 REVIEW SEAL (P1-06): UNICA autoridad — los botones
    // 82/100/122 % escriben la MISMA preferencia persistente que lee el
    // ComboBox (gallery.artworkSize / flow.coverSize / vinyl.sleeveSize
    // según albumMode). albumZoom es solo la proyección; cualquier otra
    // opción o un reload re-deriva el MISMO valor.
    function requestAlbumZoom(value) {
        value = Math.max(0.82, Math.min(1.22, value))
        albumZoom = value
        var section = albumMode === "grid" ? "gallery"
            : albumMode === "cover" ? "flow"
            : albumMode === "vinyl" ? "vinyl" : ""
        if (section === "")
            return
        var key = albumMode === "grid" ? "artworkSize"
            : albumMode === "cover" ? "coverSize" : "sleeveSize"
        // gallery: small/medium/large · flow/vinyl: small/standard/large.
        var sizeName = value >= 1.22 ? "large"
            : value <= 0.82 ? "small"
            : albumMode === "grid" ? "medium" : "standard"
        root.updateViewPreference(section, key, sizeName)
    }

    function defaultViewPreferences() {
        return {
            activeMode: "grid", sortMode: "title", sortDescending: false,
            filterMode: "all",
            gallery: { artworkSize: "medium", spacing: "balanced",
                metadataLevel: "standard", precisionMetadata: false,
                quickActions: true, inspector: true },
            flow: { coverSize: "standard", visibleAlbums: "auto",
                depth: "standard", ambientColor: true,
                metadataLevel: "standard" },
            vinyl: { sleeveSize: "standard", spacing: "standard",
                reveal: "standard", metadataLevel: "standard",
                artworkLabel: true, inspector: true },
            chronology: { grouping: "decade", direction: "newest",
                density: "standard", metadataLevel: "standard",
                showPeriodDensity: false },
            editorial: { heroVisible: true, informationRichness: "standard",
                cachedEnrichmentVisible: true, archiveLayout: "list" },
            studioList: { density: "standard", artworkSize: "small",
                metadataLevel: "standard", precisionMetadata: true,
                inspector: true, artistColumn: true, yearColumn: true,
                tracksColumn: true, durationColumn: true, formatColumn: true }
        }
    }

    function zoomForMode(preferences, mode) {
        var value = mode === "grid" ? preferences.gallery.artworkSize
            : mode === "cover" ? preferences.flow.coverSize
            : mode === "vinyl" ? preferences.vinyl.sleeveSize : "standard"
        return value === "small" ? 0.82 : value === "large" ? 1.22 : 1.0
    }

    function applyViewPreferences(preferences) {
        if (!preferences)
            return
        albumMode = albumModes.indexOf(preferences.activeMode) !== -1
            ? preferences.activeMode : "grid"
        albumSortMode = preferences.sortMode || "title"
        albumSortDescending = Boolean(preferences.sortDescending)
        albumFilterMode = preferences.filterMode || "all"
        albumTimelineGrouping = preferences.chronology
            ? preferences.chronology.grouping : "decade"
        albumZoom = zoomForMode(preferences, albumMode)
    }

    function loadViewPreferences() {
        if (typeof settingsBridge === "undefined" || !settingsBridge)
            return
        try {
            var parsed = JSON.parse(settingsBridge.libraryViews)
            viewPreferences = parsed
            applyViewPreferences(parsed)
            // LIB-A §19: estado de columnas persistido (migración segura:
            // config ausente o parcial → defaults; album settings intactos).
            if (parsed && parsed.trackTable)
                LibraryTrackColumnState.applyConfiguration(parsed.trackTable)
        } catch (error) {
            console.warn("Library view preferences could not be decoded")
        }
    }

    function persistViewPreferences(preferences) {
        viewPreferences = preferences
        if (typeof settingsBridge !== "undefined" && settingsBridge) {
            var next = JSON.parse(JSON.stringify(preferences))
            next.trackTable = LibraryTrackColumnState.snapshot()
            settingsBridge.set_library_views(JSON.stringify(next))
        }
    }

    function updateCommonPreference(key, value) {
        var next = JSON.parse(JSON.stringify(viewPreferences))
        next[key] = value
        persistViewPreferences(next)
    }

    function updateViewPreference(section, key, value) {
        var next = JSON.parse(JSON.stringify(viewPreferences))
        if (!next[section])
            return
        next[section][key] = value
        persistViewPreferences(next)
        applyViewPreferences(next)
    }

    function resetViewPreferences(section) {
        var next = JSON.parse(JSON.stringify(viewPreferences))
        var defaults = defaultViewPreferences()
        if (!next[section] || !defaults[section])
            return
        next[section] = defaults[section]
        persistViewPreferences(next)
        applyViewPreferences(next)
    }

    function requestAlbumSort(mode) {
        albumSortMode = mode
        updateCommonPreference("sortMode", mode)
    }

    function requestAlbumSortDirection(descending) {
        albumSortDescending = descending
        updateCommonPreference("sortDescending", descending)
    }

    function requestAlbumFilter(mode) {
        albumFilterMode = mode
        updateCommonPreference("filterMode", mode)
    }

    function syncEntitySelection() {
        if (library.selectedAlbumKey !== "")
            currentTab = "albums"
        else if (library.selectedArtistKey !== "")
            currentTab = "artists"
    }

    Connections {
        target: library
        function onLibrary_changed() { root.syncEntitySelection() }
    }

    // M9-R3 CONVERGENCE SEAL: select_genre emite genre_selected — el
    // resultado visible es el tab Songs con la proyección filtrada por el
    // Bridge (contrato R4 restaurado: el usuario NUNCA queda en Genres
    // sin respuesta tras activar un género).
    Connections {
        target: library
        function onGenre_selected(_genreKey) { root.currentTab = "songs" }
    }

    Connections {
        target: typeof settingsBridge !== "undefined" ? settingsBridge : null
        ignoreUnknownSignals: true
        function onLibraryViewsChanged() { root.loadViewPreferences() }
    }

    // LIB-A §20: la persistencia de la tabla es DEBOUNCED (~250 ms) —
    // durante el resize el singleton se actualiza al instante; el JSON se
    // escribe una vez cuando el usuario se detiene. Nunca por píxel.
    Timer {
        id: trackTablePersistDebounce
        interval: 250
        repeat: false
        onTriggered: root.persistViewPreferences(root.viewPreferences)
    }

    Connections {
        target: LibraryTrackColumnState
        function onConfigurationChanged() {
            // Debounce: el estado del singleton ya cambió al instante;
            // el JSON se escribe una vez, 250 ms después del ÚLTIMO
            // cambio (drag de resize acumulado) — nunca por píxel.
            trackTablePersistDebounce.restart()
        }
    }

    Component.onCompleted: {
        syncEntitySelection()
        loadViewPreferences()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiThemeState.contentGap

        LibraryHeader {
            Layout.fillWidth: true
            currentTab: root.currentTab
            albumMode: root.albumMode
            albumSortMode: root.albumSortMode
            albumSortDescending: root.albumSortDescending
            albumFilterMode: root.albumFilterMode
            albumTimelineGrouping: root.albumTimelineGrouping
            albumZoom: root.albumZoom
            viewPreferences: root.viewPreferences
            onAlbumModeRequested: mode => root.requestAlbumMode(mode)
            onAlbumSortRequested: mode => root.requestAlbumSort(mode)
            onAlbumSortDirectionRequested: descending => root.requestAlbumSortDirection(descending)
            onAlbumFilterRequested: mode => root.requestAlbumFilter(mode)
            onAlbumTimelineGroupingRequested: mode => root.updateViewPreference("chronology", "grouping", mode)
            onAlbumZoomRequested: value => root.requestAlbumZoom(value)
            onViewPreferenceRequested: (section, key, value) =>
                root.updateViewPreference(section, key, value)
            onResetViewRequested: section => root.resetViewPreferences(section)
        }

        LibraryToolbar {
            id: libraryToolbar
            Layout.fillWidth: true
            currentTab: root.currentTab
            onCurrentTabRequested: tab => root.currentTab = tab
        }

        LibraryContentHost {
            currentTab: root.currentTab
            albumMode: root.albumMode
            albumSortMode: root.albumSortMode
            albumSortDescending: root.albumSortDescending
            albumFilterMode: root.albumFilterMode
            albumTimelineGrouping: root.albumTimelineGrouping
            albumZoom: root.albumZoom
            viewPreferences: root.viewPreferences
            browseState: albumBrowseState
            onScanRequested: libraryToolbar.performScan()
            onSortModeRequested: mode => root.requestAlbumSort(mode)
            onSortDirectionRequested: descending => root.requestAlbumSortDirection(descending)
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
