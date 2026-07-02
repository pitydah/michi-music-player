import QtQuick
import QtQuick.Controls
import MichiCover 1.0
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
        // Collect albums for this artist from bridge data
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
        anchors.margins: MichiSpacing.xl
        contentHeight: column.height + MichiSpacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiSpacing.lg

            Row {
                spacing: MichiSpacing.sm

                ActionButton {
                    text: "←"
                    variant: "ghost"
                    onClicked: root.backRequested()
                }

                Text {
                    text: root.artistName
                    color: MichiColors.textPrimary
                    font.pixelSize: MichiTypography.heroTitleSize
                    font.weight: MichiTypography.weightBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle {
                width: 120
                height: 120
                radius: 60
                color: Qt.rgba(1.0, 1.0, 1.0, 0.03)
                anchors.horizontalCenter: parent.horizontalCenter

                CoverBridge {
                    anchors.fill: parent
                    coverKey: root.artistName || "ARTIST"
                }

                Text {
                    anchors.centerIn: parent
                    text: root.artistName ? root.artistName.charAt(0).toUpperCase() : "?"
                    color: MichiColors.accentBlue
                    font.pixelSize: 42
                    font.weight: MichiTypography.weightBold
                    visible: false
                }
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
