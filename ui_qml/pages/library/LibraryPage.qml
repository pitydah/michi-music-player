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

        TabBar {
            id: tabBar
            width: parent.width
            height: 42
            background: Rectangle {
                color: "transparent"
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: MichiTheme.colors.borderSubtle
                }
            }

            TabButton {
                text: "Canciones"
                width: implicitWidth + MichiTheme.spacing.xl
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: tabBar.currentIndex === 0 ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightNormal
                contentItem: Text {
                    text: parent.text
                    color: tabBar.currentIndex === 0 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Item {
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        radius: 1
                        color: MichiTheme.colors.accentBlue
                        visible: tabBar.currentIndex === 0
                    }
                }
            }

            TabButton {
                text: "Álbumes"
                width: implicitWidth + MichiTheme.spacing.xl
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: tabBar.currentIndex === 1 ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightNormal
                contentItem: Text {
                    text: parent.text
                    color: tabBar.currentIndex === 1 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Item {
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        radius: 1
                        color: MichiTheme.colors.accentBlue
                        visible: tabBar.currentIndex === 1
                    }
                }
            }

            TabButton {
                text: "Artistas"
                width: implicitWidth + MichiTheme.spacing.xl
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: tabBar.currentIndex === 2 ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightNormal
                contentItem: Text {
                    text: parent.text
                    color: tabBar.currentIndex === 2 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Item {
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        radius: 1
                        color: MichiTheme.colors.accentBlue
                        visible: tabBar.currentIndex === 2
                    }
                }
            }

            TabButton {
                text: "Carpetas"
                width: implicitWidth + MichiTheme.spacing.xl
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: tabBar.currentIndex === 3 ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightNormal
                contentItem: Text {
                    text: parent.text
                    color: tabBar.currentIndex === 3 ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Item {
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        radius: 1
                        color: MichiTheme.colors.accentBlue
                        visible: tabBar.currentIndex === 3
                    }
                }
            }
        }

        StackLayout {
            id: stackContainer
            width: parent.width
            height: parent.height - tabBar.height
            currentIndex: tabBar.currentIndex

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
