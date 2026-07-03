import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string artistName: ""
    property var bridge: null
    property var artistAlbums: []

    signal backRequested()

    function loadArtist(name) {
        artistName = name
        if (root.bridge && typeof root.bridge.filterByArtist !== "undefined") {
            root.bridge.filterByArtist(name)
        }
        if (root.bridge && typeof root.bridge.albums !== "undefined") {
            var all = root.bridge.albums || []
            var filtered = []
            for (var i = 0; i < all.length; i++) {
                if (all[i].artist === name) {
                    filtered.push(all[i])
                }
            }
            artistAlbums = filtered
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    onClicked: root.backRequested()
                }

                Text {
                    text: root.artistName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            CoverImage {
                width: 120
                height: 120
                coverRadius: MichiTheme.radiusPill
                coverKey: root.artistName || "ARTIST"
                anchors.horizontalCenter: parent.horizontalCenter
            }

            SectionHeader {
                text: "Álbumes"
                width: parent.width
            }

            GridView {
                width: parent.width
                height: Math.min(300, (Math.ceil(artistAlbums.length / 3) * 260))
                model: artistAlbums
                cellWidth: 190
                cellHeight: 240
                clip: true
                interactive: false

                delegate: AlbumCard {
                    width: 180
                    height: 220
                    albumTitle: modelData.title || ""
                    albumArtist: modelData.artist || ""
                    trackCount: modelData.track_count || 0
                    coverId: modelData.cover_key || ""
                }
            }

            SectionHeader {
                text: "Canciones"
                width: parent.width
            }

            SongTable {
                width: parent.width
                height: 300
                songs: root.bridge ? root.bridge.songs : []
                bridge: root.bridge
            }
        }
    }
}
