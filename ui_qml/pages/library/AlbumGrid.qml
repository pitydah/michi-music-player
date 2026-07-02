import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var albums: []
    property var bridge: null

    signal albumClicked(string key, string title, string artist, int year)

    GridView {
        anchors.fill: parent
        anchors.margins: MichiSpacing.md
        model: root.albums
        cellWidth: 200
        cellHeight: 260
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        delegate: AlbumCard {
            width: 180
            height: 240
            albumTitle: modelData.title || modelData.album_key || ""
            albumArtist: modelData.artist || ""
            trackCount: modelData.track_count || 0
            coverId: modelData.cover_key || modelData.album_key || ""
            onClicked: root.albumClicked(
                modelData.album_key || "",
                modelData.title || modelData.album_key || "",
                modelData.artist || "",
                modelData.year || 0
            )
        }
    }
}
