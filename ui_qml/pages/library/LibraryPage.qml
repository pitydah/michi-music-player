import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Biblioteca"

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property bool _searchActive: false
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var sel: typeof librarySelectionController !== "undefined" ? librarySelectionController : (typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null)
    property var act: typeof actionRegistry !== "undefined" ? actionRegistry : null

    objectName: "library.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Biblioteca"
    Accessible.description: "Panel principal de la biblioteca musical"

    PageStateManager {
        id: pageState
        route: "library"
        active: true
        onScrollYChanged: pageState.save()
        onCurrentTabChanged: pageState.save()
        onSearchTextChanged: pageState.save()
    }

    enum State {
        INITIALIZING,
        NO_SOURCES,
        SCANNING,
        LOADING,
        READY,
        FILTERED_EMPTY,
        SOURCE_OFFLINE,
        QUERY_ERROR,
        DATABASE_ERROR,
        CANCELLED
    }

    property int libraryState: LibraryPage.INITIALIZING

    function refreshData() {
        if (root.lib && typeof root.lib.refresh !== "undefined") {
            root.lib.refresh()
            if (root.notif) root.notif.showMessage("Biblioteca actualizada", "info")
        }
    }

    function clearFilters() {
        navBar.clearSearch()
        filterBar.clearAll()
        if (root.lib && typeof root.lib.clearFilters !== "undefined")
            root.lib.clearFilters()
        _updateState()
    }

    function showArtistDetail(name) {
        if (typeof navigationBridge !== "undefined") {
            navigationBridge.navigateWithParams("library.artist_detail", {artist: name})
        }
    }

    function showAlbumDetail(key, title, artist, year) {
        if (typeof navigationBridge !== "undefined") {
            navigationBridge.navigateWithParams("library.album_detail", {album_key: key})
        }
    }

    enum State {
        INITIALIZING,
        NO_SOURCES,
        SCANNING,
        LOADING,
        READY,
        FILTERED_EMPTY,
        SOURCE_OFFLINE,
        QUERY_ERROR,
        DATABASE_ERROR,
        CANCELLED,
        UNAVAILABLE
    }

    property int libraryState: root.lib ? LibraryPage.INITIALIZING : LibraryPage.UNAVAILABLE

    function _updateState() {
        if (!root.lib) return
        var s = root.lib.state || "INITIALIZING"
        switch (s) {
            case "NO_SOURCES": libraryState = LibraryPage.NO_SOURCES; break
            case "SCANNING": libraryState = LibraryPage.SCANNING; break
            case "LOADING": libraryState = LibraryPage.LOADING; break
            case "READY":
                if (navBar.searchText !== "" && root.lib.songCount === 0)
                    libraryState = LibraryPage.FILTERED_EMPTY
                else
                    libraryState = LibraryPage.READY
                break
            case "FILTERED_EMPTY": libraryState = LibraryPage.FILTERED_EMPTY; break
            case "SOURCE_OFFLINE": libraryState = LibraryPage.SOURCE_OFFLINE; break
            case "QUERY_ERROR": libraryState = LibraryPage.QUERY_ERROR; break
            case "DATABASE_ERROR": libraryState = LibraryPage.DATABASE_ERROR; break
            case "CANCELLED": libraryState = LibraryPage.CANCELLED; break
            default: libraryState = LibraryPage.INITIALIZING
        }
    }

    function onTrackContextMenu(trackId, trackTitle, trackArtist, trackAlbum) {
        if (typeof contextMenu !== "undefined") {
            contextMenu.trackId = trackId
            contextMenu.trackTitle = trackTitle
            contextMenu.trackArtist = trackArtist
            contextMenu.trackAlbum = trackAlbum
            contextMenu.open()
    onLibraryStateChanged: {
        if (libraryState === LibraryPage.READY && focusScope) {
            focusScope.forceActiveFocus()
        }
    }

    function onSelectionAction(actionId, ids) {
        if (!root.act) return
        root.act.execute(actionId, ids)
        if (selectionBar) selectionBar.clearSelection()
    }

    Column {
        anchors.fill: parent; spacing: MichiTheme.spacing.xs

        LibraryNavigationBar {
            id: navBar; width: parent.width
            objectName: "libraryNavBar"
            Accessible.name: "Barra de navegación de biblioteca"
            onSearchTextUpdated: { if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(text); root._searchActive = text.length > 0; pageState.searchText = text }
            Keys.onReturnPressed: { if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(navBar.searchText) }
            Keys.onEscapePressed: { navBar.clearSearch(); root._searchActive = false; pageState.searchText = "" }
            activeFocusOnTab: true
        }

        LibraryFilterBar {
            id: filterBar; width: parent.width
            objectName: "libraryFilterBar"
            Accessible.name: "Filtros de biblioteca"
            activeFocusOnTab: true
            onFormatFilterChanged: function(fmt) { if (root.lib) root.lib.setFormatFilter(fmt) }
            onGenreFilterChanged: function(genre) { if (root.lib) root.lib.setGenreFilter(genre) }
            onYearFilterChanged: function(year) { if (root.lib) root.lib.setYearFilter(year) }
        }

        LibraryStatusHeader {
            id: statusHeader; width: parent.width
            visible: root.lib && (root.lib.songCount > 0 || root.lib.state !== "READY")
            songCount: root.lib ? root.lib.songCount : 0
            albumCount: root.lib ? root.lib.albumCount : 0
            artistCount: root.lib ? root.lib.artistCount : 0
            state: root.lib ? root.lib.state : "INITIALIZING"
            objectName: "libraryStatusHeader"
            Accessible.name: "Estado de la biblioteca"
        }

        StackLayout {
            id: stackContainer
            width: parent.width
            height: parent.height - navBar.height - filterBar.height - statusHeader.height - selectionBar.height
            currentIndex: pageState.hasSavedState() ? pageState.currentTab : navBar.currentTab
            onCurrentIndexChanged: { if (activeFocus) pageState.currentTab = currentIndex }

            FocusScope {
                id: tracksFocusScope
                objectName: "tracksFocusScope"
                Accessible.name: "Lista de canciones"
                focus: navBar.currentTab === 0

                LibraryTrackTable {
                    id: tracksView
                    anchors.fill: parent
                    trackModel: root.lib ? root.lib.trackModel : null
                    bridge: root.lib
                    notif: root.notif
                    actionRegistry: root.act
                    selectionController: root.sel
                    objectName: "libraryTrackTable"
                    Accessible.name: "Lista de canciones"
                    activeFocusOnTab: true
                    onTrackContextMenuRequested: function(trackId, title, artist, album) {
                        root.onTrackContextMenu(trackId, title, artist, album)
                    }
                }
            }

            FocusScope {
                id: albumsFocusScope
                objectName: "albumsFocusScope"
                Accessible.name: "Cuadrícula de álbumes"
                focus: navBar.currentTab === 1

                AlbumGridPage {
                    id: albumGrid
                    anchors.fill: parent
                    albumModel: root.lib ? root.lib.albumModel : null
                    bridge: root.lib
                    objectName: "albumGridPage"
                    Accessible.name: "Cuadrícula de álbumes"
                    activeFocusOnTab: true
                    onAlbumClicked: function(key, title, artist, year) { root.showAlbumDetail(key, title, artist, year) }
                }
            }

            FocusScope {
                id: artistsFocusScope
                objectName: "artistsFocusScope"
                Accessible.name: "Cuadrícula de artistas"
                focus: navBar.currentTab === 2

                ArtistGridPage {
                    id: artistGrid
                    anchors.fill: parent
                    artistModel: root.lib ? root.lib.artistModel : null
                    bridge: root.lib
                    objectName: "artistGridPage"
                    Accessible.name: "Cuadrícula de artistas"
                    activeFocusOnTab: true
                    onArtistClicked: function(name) { root.showArtistDetail(name) }
                }
            }

            FocusScope {
                id: foldersFocusScope
                objectName: "foldersFocusScope"
                Accessible.name: "Explorador de carpetas"
                focus: navBar.currentTab === 3

                FolderBrowserPage {
                    id: folderBrowser
                    anchors.fill: parent
                    folderModel: root.lib ? root.lib.folderModel : null
                    bridge: root.lib
                    objectName: "folderBrowserPage"
                    Accessible.name: "Explorador de carpetas"
                    activeFocusOnTab: true
                }
            }
        }

        LibrarySelectionBar {
            id: selectionBar
            width: parent.width
            height: MichiTheme.toolbarHeight
            z: 10
            objectName: "librarySelectionBar"
            Accessible.name: "Barra de selección"
            bridge: root.lib
            visible: selectedCount > 0
            onActionRequested: function(actionId, ids) {
                root.onSelectionAction(actionId, ids)
            }
            onSelectionCleared: {
                if (root.sel && typeof root.sel.clear !== "undefined")
                    root.sel.clear()
            }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.CANCELLED
        z: 10
        sourceComponent: CancellationState {
            title: "Operación cancelada"
            message: "La carga de la biblioteca fue cancelada."
            objectName: "library.cancelledState"
            Accessible.name: "Biblioteca cancelada"
        }
    }

    FocusScope {
        id: focusScope
        visible: libraryState !== LibraryPage.UNAVAILABLE && libraryState !== LibraryPage.CANCELLED
        anchors.fill: parent
        objectName: "library.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.sel && root.sel.hasSelection) {
                root.sel.clear()
            } else {
                root.clearFilters()
            }
        }

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Tab) {
                if (focusScope.focus) {
                    navBar.forceActiveFocus()
                }
            }
            if (event.key === Qt.Key_A && (event.modifiers & Qt.ControlModifier)) {
                if (root.sel && tracksView && tracksView.selectAll) {
                    tracksView.selectAll()
                }
            }
        }

        Column {
            anchors.fill: parent
            spacing: 0

            LibraryNavigationBar {
                id: navBar
                width: parent.width
                objectName: "library.navBar"
                Accessible.name: "Barra de navegación de biblioteca"
                onSearchTextUpdated: function(text) {
                    if (root.lib && typeof root.lib.search !== "undefined") {
                        root.lib.search(text)
                        _updateState()
                    }
                }
                KeyNavigation.tab: filterBar
                KeyNavigation.down: filterBar
            }

            LibraryFilterBar {
                id: filterBar
                width: parent.width
                objectName: "library.filterBar"
                Accessible.name: "Barra de filtros"
                onFormatFilterChanged: function(fmt) { if (root.lib) root.lib.setFormatFilter(fmt); _updateState() }
                onGenreFilterChanged: function(genre) { if (root.lib) root.lib.setGenreFilter(genre); _updateState() }
                onYearFilterChanged: function(year) { if (root.lib) root.lib.setYearFilter(year); _updateState() }
                KeyNavigation.tab: statusHeader
                KeyNavigation.backtab: navBar
                KeyNavigation.down: statusHeader
            }

            LibraryStatusHeader {
                id: statusHeader
                width: parent.width
                objectName: "library.statusHeader"
                Accessible.name: "Estado de la biblioteca"
                visible: root.lib && (root.lib.songCount > 0 || root.lib.state !== "READY")
                songCount: root.lib ? root.lib.songCount : 0
                albumCount: root.lib ? root.lib.albumCount : 0
                artistCount: root.lib ? root.lib.artistCount : 0
                state: root.lib ? root.lib.state : "INITIALIZING"
                KeyNavigation.tab: stackContainer
                KeyNavigation.backtab: filterBar
                KeyNavigation.down: stackContainer
            }

            StackLayout {
                id: stackContainer
                width: parent.width
                height: parent.height - navBar.height - filterBar.height - statusHeader.height
                currentIndex: navBar.currentTab
                objectName: "library.stackContainer"

                FocusScope {
                    id: tracksTabScope
                    objectName: "library.tracksTabScope"
                    Accessible.name: "Pestaña de canciones"

                    LibraryTrackTable {
                        id: tracksView
                        anchors.fill: parent
                        trackModel: root.lib ? root.lib.trackModel : null
                        bridge: root.lib
                        notif: root.notif
                        actionRegistry: root.act
                        selectionController: root.sel
                        KeyNavigation.backtab: statusHeader
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Tab && !(event.modifiers & Qt.ShiftModifier)) {
                                navBar.forceActiveFocus()
                            }
                        }
                    }
                }

                FocusScope {
                    id: albumsTabScope
                    objectName: "library.albumsTabScope"
                    Accessible.name: "Pestaña de álbumes"

                    AlbumGridPage {
                        anchors.fill: parent
                        albumModel: root.lib ? root.lib.albumModel : null
                        bridge: root.lib
                        onAlbumClicked: function(key, title, artist, year) { root.showAlbumDetail(key, title, artist, year) }
                        KeyNavigation.backtab: statusHeader
                    }
                }

                FocusScope {
                    id: artistsTabScope
                    objectName: "library.artistsTabScope"
                    Accessible.name: "Pestaña de artistas"

                    ArtistGridPage {
                        anchors.fill: parent
                        artistModel: root.lib ? root.lib.artistModel : null
                        bridge: root.lib
                        onArtistClicked: function(name) { root.showArtistDetail(name) }
                        KeyNavigation.backtab: statusHeader
                    }
                }

                FocusScope {
                    id: foldersTabScope
                    objectName: "library.foldersTabScope"
                    Accessible.name: "Pestaña de carpetas"

                    FolderBrowserPage {
                        anchors.fill: parent
                        folderModel: root.lib ? root.lib.folderModel : null
                        bridge: root.lib
                        KeyNavigation.backtab: statusHeader
                    }
                }

                FocusScope {
                    id: sourcesTabScope
                    objectName: "library.sourcesTabScope"
                    Accessible.name: "Pestaña de fuentes"
                    visible: navBar.currentTab === 4

                    SourcesPage {
                        anchors.fill: parent
                        bridge: root.lib
                        lib: root.lib
                    }
    function onTrackContextMenu(trackId, trackTitle, trackArtist, trackAlbum) {
        if (typeof contextMenu !== "undefined") {
            contextMenu.trackId = trackId
            contextMenu.trackTitle = trackTitle
            contextMenu.trackArtist = trackArtist
            contextMenu.trackAlbum = trackAlbum
            contextMenu.open()
        }
    }

    function onSelectionAction(actionId, ids) {
        if (!root.act) return
        root.act.execute(actionId, ids)
        if (selectionBar) selectionBar.clearSelection()
    }

    Column {
        anchors.fill: parent; spacing: MichiTheme.spacing.xs

        LibraryNavigationBar {
            id: navBar; width: parent.width
            objectName: "libraryNavBar"
            Accessible.name: "Barra de navegación de biblioteca"
            onSearchTextUpdated: { if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(text); root._searchActive = text.length > 0; pageState.searchText = text }
            Keys.onReturnPressed: { if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(navBar.searchText) }
            Keys.onEscapePressed: { navBar.clearSearch(); root._searchActive = false; pageState.searchText = "" }
            activeFocusOnTab: true
        }

        LibraryFilterBar {
            id: filterBar; width: parent.width
            objectName: "libraryFilterBar"
            Accessible.name: "Filtros de biblioteca"
            activeFocusOnTab: true
            onFormatFilterChanged: function(fmt) { if (root.lib) root.lib.setFormatFilter(fmt) }
            onGenreFilterChanged: function(genre) { if (root.lib) root.lib.setGenreFilter(genre) }
            onYearFilterChanged: function(year) { if (root.lib) root.lib.setYearFilter(year) }
        }

        LibraryStatusHeader {
            id: statusHeader; width: parent.width
            visible: root.lib && (root.lib.songCount > 0 || root.lib.state !== "READY")
            songCount: root.lib ? root.lib.songCount : 0
            albumCount: root.lib ? root.lib.albumCount : 0
            artistCount: root.lib ? root.lib.artistCount : 0
            state: root.lib ? root.lib.state : "INITIALIZING"
            objectName: "libraryStatusHeader"
            Accessible.name: "Estado de la biblioteca"
        }

        StackLayout {
            id: stackContainer
            width: parent.width
            height: parent.height - navBar.height - filterBar.height - statusHeader.height - selectionBar.height
            currentIndex: pageState.hasSavedState() ? pageState.currentTab : navBar.currentTab
            onCurrentIndexChanged: { if (activeFocus) pageState.currentTab = currentIndex }

            FocusScope {
                id: tracksFocusScope
                objectName: "tracksFocusScope"
                Accessible.name: "Lista de canciones"
                focus: navBar.currentTab === 0

                LibraryTrackTable {
                    id: tracksView
                    anchors.fill: parent
                    trackModel: root.lib ? root.lib.trackModel : null
                    bridge: root.lib
                    notif: root.notif
                    actionRegistry: root.act
                    selectionController: root.sel
                    objectName: "libraryTrackTable"
                    Accessible.name: "Lista de canciones"
                    activeFocusOnTab: true
                    onTrackContextMenuRequested: function(trackId, title, artist, album) {
                        root.onTrackContextMenu(trackId, title, artist, album)
                    }
                }
            }

            FocusScope {
                id: albumsFocusScope
                objectName: "albumsFocusScope"
                Accessible.name: "Cuadrícula de álbumes"
                focus: navBar.currentTab === 1

                AlbumGridPage {
                    id: albumGrid
                    anchors.fill: parent
                    albumModel: root.lib ? root.lib.albumModel : null
                    bridge: root.lib
                    objectName: "albumGridPage"
                    Accessible.name: "Cuadrícula de álbumes"
                    activeFocusOnTab: true
                    onAlbumClicked: function(key, title, artist, year) { root.showAlbumDetail(key, title, artist, year) }
                }
            }

            FocusScope {
                id: artistsFocusScope
                objectName: "artistsFocusScope"
                Accessible.name: "Cuadrícula de artistas"
                focus: navBar.currentTab === 2

                ArtistGridPage {
                    id: artistGrid
                    anchors.fill: parent
                    artistModel: root.lib ? root.lib.artistModel : null
                    bridge: root.lib
                    objectName: "artistGridPage"
                    Accessible.name: "Cuadrícula de artistas"
                    activeFocusOnTab: true
                    onArtistClicked: function(name) { root.showArtistDetail(name) }
                }
            }

            FocusScope {
                id: foldersFocusScope
                objectName: "foldersFocusScope"
                Accessible.name: "Explorador de carpetas"
                focus: navBar.currentTab === 3

                FolderBrowserPage {
                    id: folderBrowser
                    anchors.fill: parent
                    folderModel: root.lib ? root.lib.folderModel : null
                    bridge: root.lib
                    objectName: "folderBrowserPage"
                    Accessible.name: "Explorador de carpetas"
                    activeFocusOnTab: true
                }
            }
        }

        LibrarySelectionBar {
            id: selectionBar
            width: parent.width
            height: MichiTheme.toolbarHeight
            z: 10
            objectName: "librarySelectionBar"
            Accessible.name: "Barra de selección"
            bridge: root.lib
            visible: selectedCount > 0
            onActionRequested: function(actionId, ids) {
                root.onSelectionAction(actionId, ids)
            }
            onSelectionCleared: {
                if (root.sel && typeof root.sel.clear !== "undefined")
                    root.sel.clear()
            }
        }
    }

    LibraryContextMenu {
        id: contextMenu
        objectName: "libraryContextMenu"
        Accessible.name: "Menú contextual de biblioteca"
        bridge: root.lib
        actionRegistry: root.act
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.NO_SOURCES
        sourceComponent: LibraryEmptyState {
            title: "Sin fuentes configuradas"
            message: "Agrega carpetas de música para comenzar"
            actionText: "Añadir fuente"
            objectName: "library.noSourcesState"
            Accessible.name: "Sin fuentes"
            onActionRequested: {
                if (typeof navigationBridge !== "undefined")
                    navigationBridge.navigate("library.sources")
            }
            title: "Sin fuentes"
            message: "No hay fuentes de música configuradas. Agrega carpetas en Ajustes."
            actionText: "Configurar fuentes"
            onActionRequested: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("settings") }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.FILTERED_EMPTY
        sourceComponent: LibraryEmptyState {
            title: "Sin resultados"
            message: "No se encontraron elementos con los filtros actuales."
            actionText: "Limpiar filtros"
            message: "No se encontraron resultados con los filtros actuales"
            actionText: "Limpiar filtros"
            objectName: "library.filteredEmptyState"
            Accessible.name: "Sin resultados de filtro"
            message: "No se encontraron elementos con los filtros actuales."
            actionText: "Limpiar filtros"
            onActionRequested: root.clearFilters()
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.SOURCE_OFFLINE
        sourceComponent: LibraryEmptyState {
        sourceComponent: LibraryErrorState {
            title: "Fuente no disponible"
            message: "La fuente de biblioteca configurada no está disponible en este momento."
            actionText: "Reintentar"
            objectName: "library.sourceOfflineState"
            Accessible.name: "Fuente fuera de línea"
        sourceComponent: LibraryEmptyState {
            title: "Fuente no disponible"
            message: "La fuente de biblioteca configurada no está disponible en este momento."
            actionText: "Reintentar"
            onActionRequested: root.refreshData()
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.QUERY_ERROR || libraryState === LibraryPage.DATABASE_ERROR
        active: libraryState === LibraryPage.QUERY_ERROR
        sourceComponent: LibraryErrorState {
            title: "Error de biblioteca"
            message: root.lib ? root.lib.errorMessage : "Ocurrió un error al acceder a la biblioteca."
            actionText: "Reintentar"
            objectName: "library.queryErrorState"
            Accessible.name: "Error de consulta"
            onActionRequested: root.refreshData()
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.DATABASE_ERROR
        sourceComponent: LibraryErrorState {
            title: "Error de base de datos"
            message: "Ocurrió un error en la base de datos de la biblioteca"
            actionText: "Reintentar"
            objectName: "library.databaseErrorState"
            Accessible.name: "Error de base de datos"
        active: libraryState === LibraryPage.QUERY_ERROR || libraryState === LibraryPage.DATABASE_ERROR
        sourceComponent: LibraryErrorState {
            title: "Error de biblioteca"
            message: root.lib ? root.lib.errorMessage : "Ocurrió un error al acceder a la biblioteca."
            actionText: "Reintentar"
            onActionRequested: root.refreshData()
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.INITIALIZING || libraryState === LibraryPage.LOADING || libraryState === LibraryPage.SCANNING
        sourceComponent: Item {
            id: loadingContainer
            width: 120; height: 120
            objectName: "library.loadingState"
            Accessible.name: "Cargando biblioteca"
            BusyIndicator {
                anchors.centerIn: parent
                running: true
                Accessible.role: Accessible.Indicator
                Accessible.name: "Cargando biblioteca"
                Accessible.description: "La biblioteca se está cargando"
                Accessible.role: Accessible.Indicator
            }
        }
    }

    LibrarySelectionBar {
        id: selectionBar
        width: parent.width
        height: 40
        y: parent.height - height
        z: 10
        visible: root.sel ? root.sel.hasSelection : false
        count: root.sel ? root.sel.count : 0
        selectionController: root.sel
        objectName: "library.selectionBar"
    Connections {
        target: root.lib
        function onStateChanged() { root._updateState() }
        function onDataChanged() { root._updateState() }
    }
}
