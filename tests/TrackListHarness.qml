import QtQuick
import "../src/michi/presentation/qml/playlists"

Item {
    id: root
    width: 800
    height: 600
    property var rows: []
    signal playTrackRequested(int index)

    PlaylistTrackList {
        id: trackList
        objectName: "trackListView"
        anchors.fill: parent
        rows: root.rows
        heroComponent: null
        onPlayTrackRequested: index => root.playTrackRequested(index)
    }
}
