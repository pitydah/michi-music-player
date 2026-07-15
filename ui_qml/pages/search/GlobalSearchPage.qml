import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Búsqueda global"

    property var bridge: typeof globalSearchBridge !== "undefined" ? globalSearchBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property string _query: ""
    property var _groupedResults: []
    property bool _searching: false
    property string _errorCode: ""
    property string _errorMessage: ""
    property var _recentQueries: []
    property int _requestGen: 0
    property int _debounceTimer: 0
    property bool _filterDrawerOpen: false
    property var _typeFilters: null
    property int _yearFrom: 0
    property int _yearTo: 0
    property string _qualityFilter: "any"

    PageStateManager {
        id: pageState
        route: "search"
        active: true
        onSearchTextChanged: pageState.save()
        onScrollYChanged: pageState.save()
    }

    objectName: "globalSearchPage"

    function search(text) {
        root._requestGen++
        var gen = root._requestGen
        root._query = text

        if (root._debounceTimer) {
            root._debounceTimer = 0
        }

        if (!text || text.trim() === "") {
            root._groupedResults = []
            root._searching = false
            root._errorCode = ""
            root._errorMessage = ""
            return
        }

        root._errorCode = ""
        root._errorMessage = ""

        root._debounceTimer = Qt.callLater(function() {
            if (gen !== root._requestGen) return
            if (root._debounceTimer) {
                root._debounceTimer = 0
            }
            root._searching = true

            if (root.bridge && typeof root.bridge.search !== "undefined") {
                var result = root.bridge.search(text)
                if (gen !== root._requestGen) return
                if (result && result.ok) {
                    var items = root.bridge.results || []
                    var groups = {}
                    for (var i = 0; i < items.length; i++) {
                        var sec = items[i].section || "Otros"
                        if (root._typeFilters) {
                            var secKey = sec.toLowerCase()
                            if (root._typeFilters[secKey] === false) continue
                        }
                        if (!groups[sec]) groups[sec] = []
                        groups[sec].push(items[i])
                    }
                    var grouped = []
                    var sectionOrder = ["Canciones", "Álbumes", "Artistas", "Playlists", "Carpetas", "Géneros", "Radio", "Dispositivos", "Servidores", "Acciones", "Ajustes", "Otros"]
                    for (var si = 0; si < sectionOrder.length; si++) {
                        if (groups[sectionOrder[si]]) {
                            grouped.push({section: sectionOrder[si], items: groups[sectionOrder[si]]})
                        }
                    }
                    for (var key in groups) {
                        var found = false
                        for (var fi = 0; fi < sectionOrder.length; fi++) {
                            if (key === sectionOrder[fi]) { found = true; break }
                        }
                        if (!found) grouped.push({section: key, items: groups[key]})
                    }
                    root._groupedResults = grouped
                    root._searching = false
                    root._errorCode = ""
                    root._errorMessage = ""
                    if (text.trim() !== "" && grouped.length > 0) {
                        var q = text.trim()
                        if (root._recentQueries.indexOf(q) < 0) {
                            root._recentQueries.unshift(q)
                            if (root._recentQueries.length > 10) root._recentQueries.pop()
                        }
                    }
                } else {
                    root._groupedResults = []
                    root._searching = false
                    root._errorCode = root.bridge.errorCode || "SEARCH_FAILED"
                    root._errorMessage = root.bridge.errorMessage || "La búsqueda falló"
                }
            } else {
                root._groupedResults = []
                root._searching = false
                root._errorCode = "NO_BRIDGE"
                root._errorMessage = "No hay puente de búsqueda disponible"
            }
        }, 300)
    }

    function retry() {
        if (root._query) root.search(root._query)
    }

    function clearQuery() {
        root._query = ""
        root._groupedResults = []
        root._searching = false
        root._errorCode = ""
        root._errorMessage = ""
        recentColumn.visible = true
    }

    function applyFilters(typeFilters, yearFrom, yearTo, quality) {
        root._typeFilters = typeFilters
        root._yearFrom = yearFrom
        root._yearTo = yearTo
        root._qualityFilter = quality
        if (root._query) root.search(root._query)
    }

    function resetFilters() {
        root._typeFilters = null
        root._yearFrom = 0
        root._yearTo = 0
        root._qualityFilter = "any"
        if (root._query) root.search(root._query)
    }

    function getDomainIcon() {
        return "\u2315"
    }

    Component.onCompleted: {
        if (root.bridge && typeof root.bridge.refresh !== "undefined")
            root.bridge.refresh()
        searchGuard.checkCapability(root.bridge)
    }

    CapabilityGuard {
        id: searchGuard
        anchors.fill: parent
        capabilityName: "command_palette"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                id: searchHero
                width: parent.width
                height: 180
                radius: MichiTheme.radiusLg
                showGlow: true
                objectName: "searchHero"
                Accessible.name: "Búsqueda global"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.md

                    Row {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Búsqueda global"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item { width: parent.width - 320; height: 1 }

                        MichiButton {
                            text: "Filtros"
                            variant: "ghost"
                            anchors.verticalCenter: parent.verticalCenter
                            iconText: "\u2630"
                            objectName: "openFiltersBtn"
                            Accessible.name: "Abrir filtros de búsqueda"
                            onClicked: filterDrawer.open()
                        }

                        MichiButton {
                            text: "Limpiar"
                            variant: "ghost"
                            anchors.verticalCenter: parent.verticalCenter
                            visible: root._query !== ""
                            objectName: "clearSearchBtn"
                            Accessible.name: "Limpiar búsqueda"
                            onClicked: {
                                globalSearchInput.text = ""
                                root.clearQuery()
                            }
                        }
                    }

                    SearchField {
                        id: globalSearchInput
                        width: parent.width * 0.7
                        placeholderText: "Canciones, álbumes, artistas, playlists..."
                        objectName: "globalSearchInput"
                        Accessible.name: "Buscar canciones, álbumes, artistas, playlists"
                        Accessible.description: "Escribe para buscar en toda la biblioteca"
                        onSearchTextChanged: root.search(text)
                        activeFocusOnTab: true
                        KeyNavigation.tab: resultsFlickable
                        KeyNavigation.backtab: root
                        Keys.onReturnPressed: root.search(text)
                        Keys.onEscapePressed: {
                            text = ""
                            root.clearQuery()
                        }
                    }
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

            SearchRecentQueries {
                id: recentColumn
                width: parent.width
                recentQueries: root._recentQueries
                bridge: root.bridge
                visible: root._query === "" && root._recentQueries.length > 0
                onQueryClicked: function(text) {
                    globalSearchInput.text = text
                    root.search(text)
                }
                onClearRecent: {
                    root._recentQueries = []
                }
            }

            SearchSuggestions {
                id: suggestionsColumn
                width: parent.width
                bridge: root.bridge
                visible: root._query === "" && root._recentQueries.length === 0
                onSuggestionClicked: function(text) {
                    globalSearchInput.text = text
                    root.search(text)
                }
            }

            Text {
                id: searchingText
                visible: root._searching
                text: "Buscando..."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                Accessible.name: "Buscando"
                Accessible.role: Accessible.Indicator
            }

            ErrorState {
                id: errorState
                width: parent.width
                visible: root._errorCode !== "" && !root._searching
                title: "Error de búsqueda"
                message: root._errorMessage
                errorCode: root._errorCode
                showRetry: true
                onRetryRequested: root.retry()
            }

            Text {
                id: noResultsText
                visible: !root._searching && root._errorCode === "" && root._query !== "" && root._groupedResults.length === 0
                text: "Sin resultados para \"" + root._query + "\""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                Accessible.name: "Sin resultados para " + root._query
            }

            Flickable {
                id: resultsFlickable
                width: parent.width
                height: parent.height - (searchHero.height + MichiTheme.spacing.xl * 2 + (recentColumn.visible ? recentColumn.height + MichiTheme.spacing.lg : 0) + (errorState.visible ? 120 : 0) + (noResultsText.visible ? 30 : 0) + 60)
                contentHeight: resultsColumn.height + MichiTheme.spacing.lg
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                activeFocusOnTab: true
                visible: root._groupedResults.length > 0
                KeyNavigation.backtab: globalSearchInput
                KeyNavigation.tab: root

                Column {
                    id: resultsColumn
                    width: parent.width
                    spacing: MichiTheme.spacing.lg

                    Repeater {
                        model: root._groupedResults

                        SearchResultSection {
                            width: parent.width
                            sectionType: (modelData.section || "Otros").toLowerCase()
                            sectionTitle: modelData.section || ""
                            sectionItems: modelData.items || []
                            resultCount: modelData.items ? modelData.items.length : 0
                            isLoading: false
                            sectionEmpty: !modelData.items || modelData.items.length === 0
                            bridge: root.bridge
                            objectName: "searchResultSection_" + index
                            Accessible.name: (modelData.section || "Resultados") + " - " + (modelData.items ? modelData.items.length : 0) + " elementos"
                            activeFocusOnTab: true
                            onItemClicked: function(type, id, title, subtitle) {
                                if (root.notif && typeof root.notif.showMessage === "function") {
                                    root.notif.showMessage("Abriendo: " + title, "info")
                                }
                            }
                        }
                    }
                }
            }
        }

        SearchFiltersDrawer {
            id: filterDrawer
            bridge: root.bridge
            onFiltersApplied: function(typeFilters, yearFrom, yearTo, quality) {
                root.applyFilters(typeFilters, yearFrom, yearTo, quality)
            }
            onFiltersReset: root.resetFilters()
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

        onCloseRequested: {
            root._showOverlay = false
        }
    }
}
