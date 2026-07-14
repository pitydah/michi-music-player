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
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
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
        pageStack.push("/pages/library/ArtistDetailPage.qml", {artistName: name})
    }

    function showAlbumDetail(key, title, artist, year) {
        pageStack.push("/pages/library/album/AlbumDetailPage.qml", {albumKey: key})
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
                folderModel: root.ArtistListModel ? root.lib.folderModel : null
                bridge: root.lib
            }
        }
    }

    LibraryErrorState {
        id: errorState; anchors.centerIn: parent
        visible: false
    }

    LibraryEmptyState {
        id: emptyState; anchors.centerIn: parent
        visible: false
    }

    LibrarySelectionBar {
        id: selectionBar; width: parent.width; height: 40
        z: 10; visible: false
    }
}
