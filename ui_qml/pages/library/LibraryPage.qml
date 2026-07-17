import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../components/foundations"
import "../../materials"

Item {
    objectName: "libraryPage_control"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Biblioteca"

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property bool _searchActive: false
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property var act: typeof actionRegistry !== "undefined" ? actionRegistry : null
    property string _labelArtists: "Artistas"
    property string _labelFolders: "Carpetas"
    property string _labelRefresh: "Refrescar"
    property string _albumViewMode: "modern"

    MichiResponsive { id: responsive; availableWidth: root.width }

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

    function _updateState() {
        if (!root.lib) return
        var s = root.lib.state || "INITIALIZING"
        switch (s) {
            case "NO_SOURCES": libraryState = LibraryPage.NO_SOURCES; break
            case "SCANNING": libraryState = LibraryPage.SCANNING; break
            case "LOADING": libraryState = LibraryPage.LOADING; break
            case "READY": libraryState = LibraryPage.READY; break
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
        }
    }

    function onSelectionAction(actionId, ids) {
        if (!root.act) return
        root.act.execute(actionId, ids)
        if (selectionBar) selectionBar.clearSelection()
    }

    Column {
        anchors.fill: parent; spacing: MichiTheme.spacing.xxs

        LibraryNavigationBar {
            id: navBar; width: parent.width
            onSearchTextUpdated: { if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(text); root._searchActive = text.length > 0; pageState.searchText = text }
            Keys.onReturnPressed: { if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(navBar.searchText) }
            Keys.onEscapePressed: { navBar.clearSearch(); root._searchActive = false; pageState.searchText = "" }
        }

        LibraryFilterBar {
            id: filterBar; width: parent.width
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
        }

        StackLayout {
            id: stackContainer
            width: parent.width
            height: parent.height - navBar.height - filterBar.height - statusHeader.height - selectionBar.height
            currentIndex: pageState.hasSavedState() ? pageState.currentTab : navBar.currentTab
            onCurrentIndexChanged: { if (activeFocus) pageState.currentTab = currentIndex }

            FocusScope {
                id: tracksFocusScope
                focus: navBar.currentTab === 0

                LibraryTrackTable {
                    id: tracksView
                    anchors.fill: parent
                    trackModel: root.lib ? root.lib.trackModel : null
                    bridge: root.lib
                    notif: root.notif
                    actionRegistry: root.act
                    selectionController: root.sel
                    activeFocusOnTab: true
                    onTrackContextMenuRequested: function(trackId, title, artist, album) {
                        root.onTrackContextMenu(trackId, title, artist, album)
                    }
                }
            }

            FocusScope {
                id: albumsFocusScope
                focus: navBar.currentTab === 1

                Loader {
                    id: albumViewLoader
                    anchors.fill: parent
                    active: true
                    source: root._albumViewMode === "modern"
                        ? "album/AlbumViewHost.qml"
                        : "AlbumGridPage.qml"

                    onLoaded: {
                        item.albumModel = root.lib ? root.lib.albumModel : null
                        item.bridge = root.lib
                        if (item.hasOwnProperty("albumClicked")) {
                            item.albumClicked.connect(function(key, title, artist, year) {
                                root.showAlbumDetail(key, title, artist, year)
                            })
                        }
                    }

                    onStatusChanged: {
                        if (status === Loader.Error) {
                            source = "AlbumGridPage.qml"
                        }
                    }
                }
            }

            FocusScope {
                id: artistsFocusScope
                focus: navBar.currentTab === 2

                ArtistGridPage {
                    id: artistGrid
                    anchors.fill: parent
                    artistModel: root.lib ? root.lib.artistModel : null
                    bridge: root.lib
                    activeFocusOnTab: true
                    onArtistClicked: function(name) { root.showArtistDetail(name) }
                }
            }

            FocusScope {
                id: foldersFocusScope
                focus: navBar.currentTab === 3

                FolderBrowserPage {
                    id: folderBrowser
                    anchors.fill: parent
                    folderModel: root.lib ? root.lib.folderModel : null
                    bridge: root.lib
                    activeFocusOnTab: true
                }
            }
        }

        LibrarySelectionBar {
            id: selectionBar
            width: parent.width
            height: MichiTheme.toolbarHeight
            z: 10
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
        bridge: root.lib
        actionRegistry: root.act
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.NO_SOURCES
        sourceComponent: LibraryEmptyState {
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
            onActionRequested: root.clearFilters()
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.SOURCE_OFFLINE
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
        sourceComponent: LibraryErrorState {
            title: "Error de biblioteca"
            message: root.lib ? root.lib.errorMessage : "Ocurrió un error al acceder a la biblioteca."
            actionText: "Reintentar"
            onActionRequested: root.refreshData()
        }
    }

    LoadingState {
        anchors.centerIn: parent
        visible: libraryState === LibraryPage.INITIALIZING || libraryState === LibraryPage.LOADING || libraryState === LibraryPage.SCANNING
        title: "Cargando biblioteca"
    }

    Connections {
        target: root.lib
        function onStateChanged() { root._updateState() }
        function onDataChanged() { root._updateState() }
    }
}
