import QtQuick
import QtQuick.Controls.Basic
import "../controls"

MichiMenu {
    id: root
    property var artist: null

    MenuItem { text: qsTr("Open Artist"); icon.name: "artist"; visible: root.artist !== null; onTriggered: library.select_artist(root.artist.key) }
    MenuItem { text: qsTr("Add Artist to Queue"); icon.name: "queue"; visible: root.artist !== null && library.canQueueTracks; onTriggered: library.queue_artist(root.artist.key) }
    MenuItem { text: qsTr("Add Artist to Playlist"); icon.name: "add"; visible: root.artist !== null && library.canAddTracksToPlaylists; onTriggered: library.request_artist_playlist_target(root.artist.key) }
}
