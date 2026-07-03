import QtQuick
import QtQuick.Controls
import MichiCover 1.0
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property var bridge: null

    signal backRequested()

    function loadAlbum(key, title, artist, year) {
        albumKey = key
        albumTitle = title
        albumArtist = artist
        albumYear = year
        if (root.bridge && typeof root.bridge.filterByAlbum !== "undefined") {
            root.bridge.filterByAlbum(key)
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

                ActionButton {
                    text: "←"
                    variant: "ghost"
                    onClicked: root.backRequested()
                }
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.xl

                Rectangle {
                    width: 160
                    height: 160
                    radius: MichiTheme.radiusSm
                    color: Qt.rgba(1.0, 1.0, 1.0, 0.03)
                    clip: true

                    CoverBridge {
                        anchors.fill: parent
                        coverKey: root.albumKey || "ALBUM"
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: root.albumTitle
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        text: root.albumArtist
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        visible: root.albumArtist !== ""
                    }

                    Text {
                        text: root.albumYear > 0 ? root.albumYear : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: text !== ""
                    }

                    Text {
                        text: "Canciones: " + (root.bridge ? root.bridge.songCount : 0)
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }
            }

            SectionHeader {
                text: "Canciones"
                width: parent.width
            }

            SongTable {
                width: parent.width
                height: 400
                songs: root.bridge ? root.bridge.songs : []
                bridge: root.bridge
            }
        }
    }
}
