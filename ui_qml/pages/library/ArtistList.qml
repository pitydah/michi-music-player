import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var artists: []
    property var bridge: null

    signal artistSelected(string artistName)

    GridView {
        anchors.fill: parent
        anchors.margins: MichiSpacing.md
        model: root.artists
        cellWidth: 190
        cellHeight: 220
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        delegate: ArtistCard {
            width: 180
            height: 200
            artistName: modelData.name || ""
            trackCount: modelData.track_count || 0
            albumCount: modelData.album_count || 0
            coverId: modelData.cover_key || ""
            onClicked: root.artistSelected(modelData.name || "")
        }
    }
}
