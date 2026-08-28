import QtQuick
import QtQuick.Controls.Basic
import "../controls"

MichiMenu {
    id: root
    property var album: null

    MenuItem { text: qsTr("Open Album"); icon.name: "album"; visible: root.album !== null; onTriggered: library.select_album(root.album.key) }
    MenuItem { text: qsTr("Play Album"); icon.name: "play"; visible: root.album !== null; onTriggered: library.play_album(root.album.key) }
    MenuItem { text: qsTr("Add Album to Queue"); icon.name: "queue"; visible: root.album !== null && library.canQueueTracks; onTriggered: library.queue_album(root.album.key) }
    MenuItem { text: qsTr("Add Album to Playlist"); icon.name: "add"; visible: root.album !== null && library.canAddTracksToPlaylists; onTriggered: library.request_album_playlist_target(root.album.key) }
    MichiSeparator { visible: root.album !== null && Boolean(root.album.artistKey) }
    MenuItem { text: qsTr("Go to Artist"); icon.name: "artist"; visible: root.album !== null && Boolean(root.album.artistKey); onTriggered: library.select_artist(root.album.artistKey) }
}
