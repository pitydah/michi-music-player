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
    readonly property var primaryTabs: [
        "songs", "albums", "artists", "genres", "favorites", "history",
        "recently"
    ]
    // POST-R4 P2: transición de navegación por primary tab en curso —
    // syncEntitySelection() jamás revierte la decisión del usuario durante
    // las señales intermedias (library_changed del clear_*_selection).
    property bool primaryTabNavigationInProgress: false

    // POST-R4 P2: ÚNICA autoridad de navegación hacia un primary tab.
    // Retira cualquier selección de detalle incompatible (Album/Artist
    // detail) y establece el tab; click sobre Albums/Artists desde su
    // propio detail = volver al browse raíz.
    function requestTab(tab) {
        if (primaryTabs.indexOf(tab) === -1)
            return
        primaryTabNavigationInProgress = true
        try {
            if (typeof library !== "undefined" && library) {
                if (library.selectedAlbumKey !== "")
                    library.clear_album_selection()
                if (library.selectedArtistKey !== "")
                    library.clear_artist_selection()
            }
            currentTab = tab
        } finally {
            primaryTabNavigationInProgress = false
        }
    }

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
                precisionMetadata: true, inspector: true, artistColumn: true,
                yearColumn: true, tracksColumn: true, durationColumn: true,
                formatColumn: true }
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

    // POST-R4 P6: deep-merge de preferencias persistidas contra el
    // schema ACTUAL — secciones ausentes reciben defaults, overrides
    // existentes se preservan y las keys desconocidas se descartan
    // (una instalación V1 sin flow/vinyl/chronology/editorial/studioList
    // carga sin properties undefined).
    function deepMergePreferences(stored, defaults) {
        var merged = JSON.parse(JSON.stringify(defaults))
        if (!stored || typeof stored !== "object")
            return merged
        var rootKeys = ["activeMode", "sortMode", "sortDescending", "filterMode"]
        for (var r = 0; r < rootKeys.length; ++r) {
            if (typeof stored[rootKeys[r]] !== "undefined")
                merged[rootKeys[r]] = stored[rootKeys[r]]
        }
        for (var section in defaults) {
            var defaultSection = defaults[section]
            if (!defaultSection || typeof defaultSection !== "object")
                continue
            var storedSection = stored[section]
            if (!storedSection || typeof storedSection !== "object")
                continue
            for (var key in defaultSection) {
                if (typeof storedSection[key] !== "undefined")
                    merged[section][key] = storedSection[key]
            }
        }
        return merged
    }

    function loadViewPreferences() {
        if (typeof settingsBridge === "undefined" || !settingsBridge)
            return
        try {
            var parsed = JSON.parse(settingsBridge.libraryViews)
            // POST-R4 P6: nunca `viewPreferences = parsed` directo — el
            // deep-merge con defaults + validación da a las secciones
            // ausentes sus valores por defecto.
            viewPreferences = deepMergePreferences(
                parsed, defaultViewPreferences())
            applyViewPreferences(viewPreferences)
            // LIB-A P1-A/P1-B: el estado de columnas y la autoridad de
            // query del álbum se restauran SIN emitir configurationChanged
            // (hydration — nunca un loop de persistencia).
            if (parsed && parsed.trackTable)
                LibraryTrackColumnState.applyConfiguration(
                    parsed.trackTable, false)
            if (typeof library !== "undefined" && library
                    && parsed) {
                library.set_album_query_state(
                    parsed.sortMode || "title",
                    parsed.sortDescending === true,
                    parsed.filterMode || "all")
            }
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

    // LIB-A §37: UNA autoridad — el sort/filtro semántico del álbum vive
    // en la aplicación (LibraryAlbumQueryService); la preferencia
    // persistida acompaña (misma fuente visual) pero el orden de la
    // proyección lo aplica el Bridge.
    function requestAlbumSort(mode) {
        albumSortMode = mode
        updateCommonPreference("sortMode", mode)
        if (typeof library !== "undefined" && library)
            library.set_album_sort_mode(mode)
    }

    function requestAlbumSortDirection(descending) {
        albumSortDescending = descending
        updateCommonPreference("sortDescending", descending)
        if (typeof library !== "undefined" && library)
            library.set_album_sort_descending(descending)
    }

    function requestAlbumFilter(mode) {
        albumFilterMode = mode
        updateCommonPreference("filterMode", mode)
        if (typeof library !== "undefined" && library)
            library.set_album_filter_mode(mode)
    }

    function syncEntitySelection() {
        if (primaryTabNavigationInProgress)
            return
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
    // sin respuesta tras activar un género). POST-R4 P2: la transición
    // pasa por requestTab — retira selecciones de detalle incompatibles y
    // syncEntitySelection no revierte la decisión.
    Connections {
        target: library
        function onGenre_selected(_genreKey) { root.requestTab("songs") }
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
            onCurrentTabRequested: tab => root.requestTab(tab)
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
