import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var libraryBridge: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property int _artistDetailTab: -1
    property int _albumDetailTab: -1

    function refreshData() {
        if (root.libraryBridge && typeof root.libraryBridge.refresh !== "undefined") {
            root.libraryBridge.refresh()
        }
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

        Rectangle {
            width: parent.width
            height: 48
            color: Qt.rgba(1.0, 1.0, 1.0, 0.02)

            Row {
                anchors.fill: parent
                anchors.leftMargin: MichiSpacing.xl
                spacing: MichiSpacing.md

                Text {
                    text: "Canciones"
                    color: tabBar.currentIndex === 0 ? MichiColors.accentBlue : MichiColors.textSecondary
                    font.pixelSize: MichiTypography.bodySize
                    font.weight: tabBar.currentIndex === 0 ? MichiTypography.weightSemiBold : MichiTypography.weightNormal
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tabBar.currentIndex = 0 }
                }
                Text {
                    text: "Álbumes"
                    color: tabBar.currentIndex === 1 ? MichiColors.accentBlue : MichiColors.textSecondary
                    font.pixelSize: MichiTypography.bodySize
                    font.weight: tabBar.currentIndex === 1 ? MichiTypography.weightSemiBold : MichiTypography.weightNormal
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tabBar.currentIndex = 1 }
                }
                Text {
                    text: "Artistas"
                    color: tabBar.currentIndex === 2 ? MichiColors.accentBlue : MichiColors.textSecondary
                    font.pixelSize: MichiTypography.bodySize
                    font.weight: tabBar.currentIndex === 2 ? MichiTypography.weightSemiBold : MichiTypography.weightNormal
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tabBar.currentIndex = 2 }
                }
                Text {
                    text: "Carpetas"
                    color: tabBar.currentIndex === 3 ? MichiColors.accentBlue : MichiColors.textSecondary
                    font.pixelSize: MichiTypography.bodySize
                    font.weight: tabBar.currentIndex === 3 ? MichiTypography.weightSemiBold : MichiTypography.weightNormal
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tabBar.currentIndex = 3 }
                }
            }
        }

        SearchField {
            width: parent.width
            anchors.margins: MichiSpacing.md
            placeholderText: "Buscar canciones, artistas o álbumes..."
            onSearchTextChanged: {
                if (root.libraryBridge && typeof root.libraryBridge.search !== "undefined") {
                    root.libraryBridge.search(text)
                }
            }
        }

        StackLayout {
            id: tabBar
            width: parent.width
            height: parent.height - 48 - 38
            currentIndex: 0

            SongTable {
                id: songsView
                songs: root.libraryBridge ? root.libraryBridge.songs : []
                bridge: root.libraryBridge
            }

            AlbumGrid {
                id: albumView
                albums: root.libraryBridge ? root.libraryBridge.albums : []
                bridge: root.libraryBridge
                onAlbumClicked: function(key, title, artist, year) {
                    root.showAlbumDetail(key, title, artist, year)
                }
            }

            ArtistList {
                id: artistView
                artists: root.libraryBridge ? root.libraryBridge.artists : []
                bridge: root.libraryBridge
                onArtistSelected: function(name) {
                    root.showArtistDetail(name)
                }
            }

            FolderBrowser {
                id: folderView
                folders: root.libraryBridge ? root.libraryBridge.folders : []
                bridge: root.libraryBridge
            }

            ArtistDetailPage {
                id: artistDetail
                visible: tabBar.currentIndex === 4
                bridge: root.libraryBridge
                onBackRequested: root.backFromDetail()
            }

            AlbumDetailPage {
                id: albumDetail
                visible: tabBar.currentIndex === 5
                bridge: root.libraryBridge
                onBackRequested: root.backFromDetail()
            }
        }
    }
}
