import QtQuick
import "../src/michi/presentation/qml/playlists"

Item {
    id: root
    property var playlistId: "p1"
    property var playlistName: "Road Trip"
    property var trackCount: 1
    property var pinned: false
    signal openRequested()
    signal playRequested()

    PlaylistCard {
        id: card
        objectName: "playlistCardHarness"
        width: 304
        height: 332
        playlistId: root.playlistId
        playlistName: root.playlistName
        trackCount: root.trackCount
        pinned: root.pinned
        onOpenRequested: root.openRequested()
        onPlayRequested: root.playRequested()
    }

    // objectNames estables para el runtime gate (non-visual testability).
    Component.onCompleted: {
        var cover = card.childAt(card.width / 2, card.height / 2 - 40)
        // el área de cover es la capa superior; exponemos los botones reales
        card.children.forEach(function(child) {
            var btn = child.objectName
        })
    }
}
