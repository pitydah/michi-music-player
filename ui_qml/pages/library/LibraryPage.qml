import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var sel: typeof librarySelectionController !== "undefined" ? librarySelectionController : (typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null)
    property var act: typeof actionRegistry !== "undefined" ? actionRegistry : null
    property string _labelArtists: "Artistas"
    property string _labelFolders: "Carpetas"
    property string _labelRefresh: "Refrescar"

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

    Column {
        anchors.fill: parent; spacing: 0

        LibraryNavigationBar {
            id: navBar; width: parent.width
            onSearchTextUpdated: { if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(text) }
        }

        LibraryFilterBar {
            id: filterBar; width: parent.width
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
            height: parent.height - navBar.height - filterBar.height - statusHeader.height
            currentIndex: navBar.currentTab

            LibraryTrackTable {
                id: tracksView
                trackModel: root.lib ? root.lib.trackModel : null
                bridge: root.lib
                notif: root.notif
                actionRegistry: root.act
                selectionController: root.sel
            }

            AlbumGridPage {
                albumModel: root.lib ? root.lib.albumModel : null
                bridge: root.lib
                onAlbumClicked: function(key, title, artist, year) { root.showAlbumDetail(key, title, artist, year) }
            }

            ArtistGridPage {
                artistModel: root.lib ? root.lib.artistModel : null
                bridge: root.lib
                onArtistClicked: function(name) { root.showArtistDetail(name) }
            }

            FolderBrowserPage {
                folderModel: root.lib ? root.lib.folderModel : null
                bridge: root.lib
            }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.NO_SOURCES
        sourceComponent: Text {
            text: "No hay fuentes configuradas"
            color: MichiTheme.textMuted
            font.pixelSize: MichiTheme.fontSizeLarge
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.FILTERED_EMPTY
        sourceComponent: Text {
            text: "No se encontraron resultados con los filtros actuales"
            color: MichiTheme.textMuted
            font.pixelSize: MichiTheme.fontSizeLarge
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.SOURCE_OFFLINE
        sourceComponent: Text {
            text: "Fuente de biblioteca no disponible"
            color: MichiTheme.textMuted
            font.pixelSize: MichiTheme.fontSizeLarge
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.QUERY_ERROR || libraryState === LibraryPage.DATABASE_ERROR
        sourceComponent: Text {
            text: "Error al cargar la biblioteca"
            color: MichiTheme.errorColor
            font.pixelSize: MichiTheme.fontSizeLarge
        }
    }

    Loader {
        anchors.centerIn: parent
        active: libraryState === LibraryPage.INITIALIZING || libraryState === LibraryPage.LOADING || libraryState === LibraryPage.SCANNING
        sourceComponent: Item {
            width: 120; height: 120
            BusyIndicator { anchors.centerIn: parent; running: true }
        }
    }

    LibrarySelectionBar {
        id: selectionBar; width: parent.width; height: 40
        z: 10
        visible: root.sel ? root.sel.hasSelection : false
        count: root.sel ? root.sel.count : 0
        selectionController: root.sel
    }
}
