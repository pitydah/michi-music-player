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
        anchors.fill: parent; spacing: 0

        TabBar {
            id: tabBar
            width: parent.width; height: 38
            background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: MichiTheme.colors.borderSubtle } }

            TabButton {
                text: "Canciones"
                font.pixelSize: MichiTheme.typography.bodySize
                contentItem: Text { text: parent.text; color: tabBar.currentIndex === 0 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; radius: 1; color: MichiTheme.colors.accentBlue; visible: tabBar.currentIndex === 0 } }
            }
            TabButton {
                text: "Álbumes"
                font.pixelSize: MichiTheme.typography.bodySize
                contentItem: Text { text: parent.text; color: tabBar.currentIndex === 1 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; radius: 1; color: MichiTheme.colors.accentBlue; visible: tabBar.currentIndex === 1 } }
            }
            TabButton {
                text: "Artistas"
                font.pixelSize: MichiTheme.typography.bodySize
                contentItem: Text { text: parent.text; color: tabBar.currentIndex === 2 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; radius: 1; color: MichiTheme.colors.accentBlue; visible: tabBar.currentIndex === 2 } }
            }
            TabButton {
                text: "Carpetas"
                font.pixelSize: MichiTheme.typography.bodySize
                contentItem: Text { text: parent.text; color: tabBar.currentIndex === 3 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; radius: 1; color: MichiTheme.colors.accentBlue; visible: tabBar.currentIndex === 3 } }
            }
        }

        Rectangle {
            width: parent.width; height: 40; color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                SearchField {
                    Layout.preferredWidth: 240; Layout.minimumWidth: 160; Layout.maximumWidth: 320
                    placeholderText: "Buscar..."
                    onSearchTextChanged: {
                        root._filterText = text
                        if (root.lib && typeof root.lib.search !== "undefined") root.lib.search(text)
                    }
                }

                StatusBadge { text: root.lib ? root.lib.songCount + " canciones" : ""; kind: "info"; visible: root.lib && root.lib.songCount > 0 }
                StatusBadge { text: root.lib ? root.lib.albumCount + " álbumes" : ""; kind: "info"; visible: root.lib && root.lib.albumCount > 0 }
                StatusBadge { text: root.lib ? root.lib.artistCount + " artistas" : ""; kind: "info"; visible: root.lib && root.lib.artistCount > 0 }

                Item { Layout.fillWidth: true }

                MichiButton { text: "Limpiar filtros"; variant: "ghost"; Layout.preferredWidth: 120; Layout.minimumWidth: 110; onClicked: root.clearFilters() }
                MichiButton { text: "Refrescar"; variant: "ghost"; Layout.preferredWidth: 92; Layout.minimumWidth: 84; onClicked: root.refreshData() }
            }
        }

        Flow {
            width: parent.width; height: 30; spacing: MichiTheme.spacing.xs
            leftPadding: MichiTheme.spacing.md; visible: tabBar.currentIndex === 0

            FilterChip { text: "Todos"; selected: root.lib && root.lib.activeFormatFilter === ""; onClicked: { if (root.lib) root.lib.setFormatFilter("") } }
            FilterChip { text: "FLAC"; selected: root.lib && root.lib.activeFormatFilter === "flac"; onClicked: { if (root.lib) root.lib.setFormatFilter("flac") } }
            FilterChip { text: "MP3"; selected: root.lib && root.lib.activeFormatFilter === "mp3"; onClicked: { if (root.lib) root.lib.setFormatFilter("mp3") } }
            FilterChip { text: "WAV"; selected: root.lib && root.lib.activeFormatFilter === "wav"; onClicked: { if (root.lib) root.lib.setFormatFilter("wav") } }
        }

        StackLayout {
            id: stackContainer
            width: parent.width
            height: parent.height - tabBar.height - 40 - 30
            currentIndex: tabBar.currentIndex

            SongTable { id: songsView; songs: root.lib ? root.lib.songs : []; bridge: root.lib }

            AlbumGrid {
                id: albumView; albums: root.lib ? root.lib.albums : []; bridge: root.lib
                onAlbumClicked: function(key, title, artist, year) { root.showAlbumDetail(key, title, artist, year) }
            }

            ArtistList {
                id: artistView; artists: root.lib ? root.lib.artists : []; bridge: root.lib
                onArtistSelected: function(name) { root.showArtistDetail(name) }
            }

            FolderBrowser { id: folderView; folders: root.lib ? root.lib.folders : []; bridge: root.lib }

            ArtistDetailPage { id: artistDetail; visible: tabBar.currentIndex === 4; bridge: root.lib; onBackRequested: root.backFromDetail() }
            AlbumDetailPage { id: albumDetail; visible: tabBar.currentIndex === 5; bridge: root.lib; onBackRequested: root.backFromDetail() }
        }
    }
}
