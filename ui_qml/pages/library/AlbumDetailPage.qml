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
            }

            Row {
                width: parent.width
                spacing: MichiSpacing.xl

                Rectangle {
                    width: 160
                    height: 160
                    radius: 8
                    color: Qt.rgba(1.0, 1.0, 1.0, 0.03)
                    clip: true

                    CoverBridge {
                        anchors.fill: parent
                        coverKey: root.albumKey || "ALBUM"
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiSpacing.sm

                    Text {
                        text: root.albumTitle
                        color: MichiColors.textPrimary
                        font.pixelSize: MichiTypography.heroTitleSize
                        font.weight: MichiTypography.weightBold
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        text: root.albumArtist
                        color: MichiColors.textSecondary
                        font.pixelSize: MichiTypography.sectionTitleSize
                        visible: root.albumArtist !== ""
                    }

                    Text {
                        text: root.albumYear > 0 ? root.albumYear : ""
                        color: MichiColors.textMuted
                        font.pixelSize: MichiTypography.bodySize
                        visible: text !== ""
                    }

                    Text {
                        text: "Canciones: " + (root.bridge ? root.bridge.songCount : 0)
                        color: MichiColors.textMuted
                        font.pixelSize: MichiTypography.metaSize
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
