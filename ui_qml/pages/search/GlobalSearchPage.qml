import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: typeof globalSearchBridge !== "undefined" ? globalSearchBridge : null
    property string _query: ""
    property var _groupedResults: []
    property bool _searching: false
    property string _errorCode: ""
    property string _errorMessage: ""
    property bool _hasError: false
    property int _generation: 0
    property var _sectionLoading: ({})
    property var _recentQueries: []
    property int _debounceTimer: 0
    property bool _filtersOpen: false
    property var _activeFilters: ({})
    property bool _showOverlay: false

    objectName: "globalSearch.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Búsqueda global"
    Accessible.description: "Búsqueda global de canciones, álbumes, artistas, playlists y más"

    function performSearch(text) {
        root._query = text
        if (root._debounceTimer) {
            root._debounceTimer = 0
        }
        if (!text || text.trim() === "") {
            root._groupedResults = []
            root._searching = false
            root._hasError = false
            root._errorMessage = ""
            root._sectionLoading = {}
            return
        }
        root._generation++
        var gen = root._generation
        root._searching = true
        root._hasError = false
        root._errorMessage = ""
        root._sectionLoading = {}
        function markAllLoading() {
            var sections = ["track", "album", "artist", "playlist", "folder", "genre", "radio", "device", "server", "action", "setting"]
            var loading = {}
            for (var si = 0; si < sections.length; si++) {
                loading[sections[si]] = true
            }
            root._sectionLoading = loading
        }
        markAllLoading()

        if (root.bridge && typeof root.bridge.search !== "undefined") {
            var result = root.bridge.search(text)
            if (gen !== root._generation) {
                return
            }
            if (result && result.ok) {
                var items = root.bridge.results || []
                var groups = {}
                var loadingGroups = {}
                var sections = ["track", "album", "artist", "playlist", "folder", "genre", "radio", "device", "server", "action", "setting"]
                for (var si2 = 0; si2 < sections.length; si2++) {
                    groups[sections[si2]] = []
                    loadingGroups[sections[si2]] = false
                }
                for (var i = 0; i < items.length; i++) {
                    var sec = items[i].section || "Otros"
                    if (!groups[sec]) groups[sec] = []
                    groups[sec].push(items[i])
                }
                var grouped = []
                for (var si3 = 0; si3 < sections.length; si3++) {
                    var key = sections[si3]
                    if (groups[key] && groups[key].length > 0) {
                        grouped.push({section: key, items: groups[key]})
                    }
                }
                for (var extra in groups) {
                    if (sections.indexOf(extra) < 0 && groups[extra].length > 0) {
                        grouped.push({section: extra, items: groups[extra]})
                    }
                }
                root._groupedResults = grouped
                root._sectionLoading = loadingGroups
                if (root._recentQueries.indexOf(text) < 0) {
                    root._recentQueries.unshift(text)
                    if (root._recentQueries.length > 10) root._recentQueries.pop()
                }
            } else {
                if (gen === root._generation) {
                    root._hasError = true
                    root._errorCode = (result && result.error_code) || "SEARCH_FAILED"
                    root._errorMessage = (result && result.message) || "Error al buscar"
                    root._sectionLoading = {}
                }
            }
        } else {
            if (gen === root._generation) {
                root._hasError = true
                root._errorCode = "SERVICE_UNAVAILABLE"
                root._errorMessage = "Servicio de búsqueda no disponible"
                root._sectionLoading = {}
            }
        }
        if (gen === root._generation) {
            root._searching = false
        }
    }

    function onSearchTextChanged(text) {
        if (root._debounceTimer) {
            root._debounceTimer = 0
        }
        root._debounceTimer = Qt.callLater(function() {
            root.performSearch(text)
        }, 300)
    }

    function clearSearch() {
        root._query = ""
        root._groupedResults = []
        root._searching = false
        root._hasError = false
        root._errorMessage = ""
        root._errorCode = ""
        root._sectionLoading = {}
        if (searchField) searchField.text = ""
    }

    function retrySearch() {
        root.performSearch(root._query)
    }

    function onItemClicked(type, id, title, data) {
        if (typeof navigationBridge !== "undefined" && navigationBridge) {
            if (type === "track") {
                if (root.bridge && typeof root.bridge.playTrack === "function") {
                    root.bridge.playTrack(id)
                }
            } else if (type === "album") {
                navigationBridge.navigate("album", {albumId: id})
            } else if (type === "artist") {
                navigationBridge.navigate("artist", {artistId: id})
            } else if (type === "playlist") {
                navigationBridge.navigate("playlist", {playlistId: id})
            } else if (type === "radio") {
                if (root.bridge && typeof root.bridge.playStation === "function") {
                    root.bridge.playStation(data ? data.url : "")
                }
            } else {
                navigationBridge.navigate(type, {id: id, title: title})
            }
        }
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "globalSearch.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (searchField && searchField.text !== "") {
                root.clearSearch()
            } else if (typeof navigationBridge !== "undefined" && navigationBridge) {
                navigationBridge.navigate("home")
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                id: hero
                width: parent.width
                height: 160
                radius: MichiTheme.radiusLg
                showGlow: true
                objectName: "globalSearch.hero"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Búsqueda global"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                        Accessible.role: Accessible.Heading
                        Accessible.name: "Búsqueda global"
                    }

                    Row {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm

                        SearchField {
                            id: searchField
                            width: parent.width * 0.65
                            placeholderText: "Canciones, álbumes, artistas, playlists..."
                            onSearchTextChanged: root.onSearchTextChanged(text)
                            onSearchSubmitted: root.performSearch(text)
                            onClearRequested: root.clearSearch()
                            objectName: "globalSearch.searchField"
                            Accessible.name: "Campo de búsqueda global"
                            KeyNavigation.tab: filtersButton
                        }

                        MichiButton {
                            id: filtersButton
                            text: "Filtros"
                            variant: root._filtersOpen ? "primary" : "ghost"
                            onClicked: root._filtersOpen = !root._filtersOpen
                            objectName: "globalSearch.filtersButton"
                            Accessible.name: "Abrir filtros de búsqueda"
                            KeyNavigation.tab: resultsFlickable
                            KeyNavigation.backtab: searchField
                        }

                        MichiButton {
                            text: "Búsqueda rápida"
                            variant: "ghost"
                            onClicked: root._showOverlay = true
                            objectName: "globalSearch.quickSearchButton"
                            Accessible.name: "Abrir búsqueda rápida"
                        }
                    }
                }
            }

            Loader {
                width: parent.width
                height: active ? childrenRect.height : 0
                active: root._query === "" && root._recentQueries.length > 0

                sourceComponent: SearchRecentQueries {
                    recentQueries: root._recentQueries
                    bridge: root.bridge
                    onQueryClicked: {
                        if (searchField) searchField.text = text
                        root.performSearch(text)
                    }
                    onClearRecent: root._recentQueries = []
                }
            }

            Loader {
                width: parent.width
                height: active ? childrenRect.height : 0
                active: root._query === "" && root._recentQueries.length === 0

                sourceComponent: SearchSuggestions {
                    bridge: root.bridge
                    onSuggestionClicked: {
                        if (searchField) searchField.text = text
                        root.performSearch(text)
                    }
                }
            }

            Loader {
                width: parent.width
                height: active ? childrenRect.height : 0
                active: root._hasError

                sourceComponent: ErrorState {
                    title: "Error en la búsqueda"
                    message: root._errorMessage
                    errorCode: root._errorCode
                    width: parent.width
                    onRetryRequested: root.retrySearch()
                }
            }

            Loader {
                width: parent.width
                height: active ? childrenRect.height : 0
                active: !root._searching && !root._hasError && root._query !== "" && root._groupedResults.length === 0

                sourceComponent: EmptyState {
                    iconText: "\uD83D\uDD0D"
                    title: "Sin resultados"
                    subtitle: "No se encontraron resultados para \"" + root._query + "\""
                    width: parent.width
                }
            }

            Flickable {
                id: resultsFlickable
                width: parent.width
                height: parent.height - hero.height - MichiTheme.spacing.xl * 3 - 60
                contentHeight: resultsColumn.height + MichiTheme.spacing.lg
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                focus: true
                objectName: "globalSearch.resultsFlickable"
                KeyNavigation.backtab: filtersButton

                Keys.onEscapePressed: {
                    if (searchField && searchField.text !== "") {
                        root.clearSearch()
                    } else if (typeof navigationBridge !== "undefined" && navigationBridge) {
                        navigationBridge.navigate("home")
                    }
                }

                Column {
                    id: resultsColumn
                    width: parent.width
                    spacing: MichiTheme.spacing.lg
                    objectName: "globalSearch.resultsColumn"
                    visible: root._query !== "" && !root._hasError && !(!root._searching && root._groupedResults.length === 0)

                    Repeater {
                        model: root._groupedResults

                        SearchResultSection {
                            width: parent.width
                            sectionType: modelData.section || ""
                            sectionTitle: {
                                var titles = {
                                    "track": "Canciones", "album": "Álbumes", "artist": "Artistas",
                                    "playlist": "Playlists", "folder": "Carpetas", "genre": "Géneros",
                                    "radio": "Radio", "device": "Dispositivos", "server": "Servidores",
                                    "action": "Acciones", "setting": "Ajustes"
                                }
                                return titles[modelData.section] || modelData.section || ""
                            }
                            resultCount: modelData.items ? modelData.items.length : 0
                            items: modelData.items || []
                            loading: root._sectionLoading && root._sectionLoading[modelData.section] === true
                            bridge: root.bridge
                            objectName: "globalSearch.resultSection." + (modelData.section || "unknown") + "." + index

                            onItemClicked: root.onItemClicked(type, id, title, data)
                            onRetryRequested: root.retrySearch()
                        }
                    }

                    Text {
                        width: parent.width
                        visible: root._searching
                        text: "Buscando..."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                        objectName: "globalSearch.searchingIndicator"
                    }
                }
            }
        }
    }

    SearchFiltersDrawer {
        id: filtersDrawer
        anchors.fill: parent
        open: root._filtersOpen
        bridge: root.bridge

        onApplied: function(filters) {
            root._activeFilters = filters
        }
        onReset: {
            root._activeFilters = {}
        }
    }

    GlobalSearchOverlay {
        id: overlay
        anchors.fill: parent
        visible: root._showOverlay
        bridge: root.bridge

        onNavigateTo: function(type, id, title) {
            root._showOverlay = false
            root.onItemClicked(type, id, title, null)
        }
        onCloseRequested: {
            root._showOverlay = false
        }
    }
}
