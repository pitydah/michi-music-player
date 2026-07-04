import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property int _artistDetailTab: -1
    property int _albumDetailTab: -1
    property string _filterText: ""

    function refreshData() {
        if (root.lib && typeof root.lib.refresh !== "undefined") {
            root.lib.refresh()
            if (root.notif) root.notif.showMessage("Biblioteca actualizada", "info")
        }
    }

    function clearFilters() {
        _filterText = ""
        if (root.lib && typeof root.lib.clearFilters !== "undefined")
            root.lib.clearFilters()
    }

    function showArtistDetail(name) {
        _artistDetailTab = tabBar.currentIndex
        tabBar.currentIndex = 4
        artistDetail.loadArtist(name)
    }

    function showAlbumDetail(key, title, artist, year) {
        _albumDetailTab = tabBar.currentIndex
        tabBar.currentIndex = 5
        albumDetail.loadAlbum(key, title, artist, year)
    }

    function backFromDetail() {
        if (_artistDetailTab >= 0) {
            tabBar.currentIndex = _artistDetailTab
            _artistDetailTab = -1
        } else if (_albumDetailTab >= 0) {
            tabBar.currentIndex = _albumDetailTab
            _albumDetailTab = -1
        }
    }

    Component.onCompleted: refreshData()

    Column {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: tabBar
            width: parent.width; height: 36
            background: Rectangle {
                color: "transparent"
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: MichiTheme.colors.borderSubtle }
            }

            TabButton { text: "Canciones"; width: implicitWidth + MichiTheme.spacing.lg; font.pixelSize: MichiTheme.typography.metaSize }
            TabButton { text: "Álbumes"; width: implicitWidth + MichiTheme.spacing.lg; font.pixelSize: MichiTheme.typography.metaSize }
            TabButton { text: "Artistas"; width: implicitWidth + MichiTheme.spacing.lg; font.pixelSize: MichiTheme.typography.metaSize }
            TabButton { text: "Carpetas"; width: implicitWidth + MichiTheme.spacing.lg; font.pixelSize: MichiTheme.typography.metaSize }
        }

        Rectangle {
            width: parent.width; height: 36; color: MichiTheme.colors.surfaceCard
            Row {
                anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.xs

                SearchField {
                    width: 200; height: 28; anchors.verticalCenter: parent.verticalCenter
                    placeholderText: "Buscar..."
                    onSearchTextChanged: {
                        root._filterText = text
                        if (root.lib && typeof root.lib.search !== "undefined")
                            root.lib.search(text)
                    }
                }

                StatusBadge { text: root.lib ? root.lib.songCount + " canciones" : ""; kind: "info"; anchors.verticalCenter: parent.verticalCenter; visible: root.lib && root.lib.songCount > 0 }
                StatusBadge { text: root.lib ? root.lib.albumCount + " álbumes" : ""; kind: "info"; anchors.verticalCenter: parent.verticalCenter; visible: root.lib && root.lib.albumCount > 0 }
                StatusBadge { text: root.lib ? root.lib.artistCount + " artistas" : ""; kind: "info"; anchors.verticalCenter: parent.verticalCenter; visible: root.lib && root.lib.artistCount > 0 }

                Item { Layout.fillWidth: true; width: 1; height: 1 }

                MichiButton { text: "Limpiar filtros"; variant: "ghost"; height: 24; anchors.verticalCenter: parent.verticalCenter; onClicked: root.clearFilters() }
                MichiButton { text: "Refrescar"; variant: "ghost"; height: 24; anchors.verticalCenter: parent.verticalCenter; onClicked: root.refreshData() }
            }
        }

        StackLayout {
            id: stackContainer
            width: parent.width
            height: parent.height - tabBar.height - 36
            currentIndex: tabBar.currentIndex

            SongTable { id: songsView; songs: root.lib ? root.lib.songs : []; bridge: root.lib }

            AlbumGrid {
                id: albumView
                albums: root.lib ? root.lib.albums : []
                bridge: root.lib
                onAlbumClicked: function(key, title, artist, year) { root.showAlbumDetail(key, title, artist, year) }
            }

            ArtistList {
                id: artistView
                artists: root.lib ? root.lib.artists : []
                bridge: root.lib
                onArtistSelected: function(name) { root.showArtistDetail(name) }
            }

            FolderBrowser { id: folderView; folders: root.lib ? root.lib.folders : []; bridge: root.lib }

            ArtistDetailPage { id: artistDetail; visible: tabBar.currentIndex === 4; bridge: root.lib; onBackRequested: root.backFromDetail() }
            AlbumDetailPage { id: albumDetail; visible: tabBar.currentIndex === 5; bridge: root.lib; onBackRequested: root.backFromDetail() }
        }
    }
}
