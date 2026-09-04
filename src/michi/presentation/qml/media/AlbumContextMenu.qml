import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiMenu {
    id: root
    property var album: null
    // POST-MERGE CONTEXTUAL RECOVERY: never expose an action merely
    // because a backend signal exists. The host must explicitly prove a
    // productive consumer for picker/create/properties flows.
    property bool canAddToPlaylist: false
    property bool canCreatePlaylist: false
    property bool canShowProperties: false

    Item {
        implicitWidth: 284
        implicitHeight: 56
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.sm
            anchors.rightMargin: MichiSpacing.sm
            spacing: MichiSpacing.sm
            Artwork {
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                sourcePath: root.album && root.album.hasArtwork
                    ? root.album.artworkPath : ""
                fallbackText: root.album ? root.album.title : "A"
                requestedSize: 72
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                MichiText {
                    Layout.fillWidth: true
                    text: root.album ? root.album.title : ""
                    role: "body"
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: root.album ? root.album.artist
                        + (root.album.year > 0 ? " · " + root.album.year : "") : ""
                    role: "caption"
                    elide: Text.ElideRight
                }
            }
        }
    }
    MichiSeparator { }
    MichiMenuItem {
        text: qsTr("Open Album")
        icon.name: "album"
        visible: root.album !== null
        onTriggered: library.select_album(root.album.key)
    }
    MichiMenuItem {
        text: qsTr("Play Album")
        icon.name: "play"
        visible: root.album !== null
        onTriggered: library.play_album(root.album.key)
    }
    MichiMenuItem {
        text: qsTr("Add Album to Queue")
        icon.name: "queue"
        visible: root.album !== null && library.canQueueTracks
        onTriggered: library.queue_album(root.album.key)
    }
    MichiSeparator {
        visible: root.album !== null
            && ((root.canAddToPlaylist || root.canCreatePlaylist)
                && library.canAddTracksToPlaylists)
    }
    MichiMenuItem {
        text: qsTr("Add Album to Playlist")
        icon.name: "add"
        visible: root.album !== null && root.canAddToPlaylist
            && library.canAddTracksToPlaylists
        onTriggered: library.request_album_playlist_target(root.album.key)
    }
    MichiMenuItem {
        text: qsTr("Create Playlist from Album…")
        icon.name: "plus"
        visible: root.album !== null && root.canCreatePlaylist
            && library.canAddTracksToPlaylists
        onTriggered: library.request_new_playlist_for_album(root.album.key)
    }
    MichiSeparator { visible: root.album !== null && Boolean(root.album.artistKey) }
    MichiMenuItem {
        text: qsTr("Go to Artist")
        icon.name: "artist"
        visible: root.album !== null && Boolean(root.album.artistKey)
        onTriggered: library.select_artist(root.album.artistKey)
    }
    MichiSeparator { visible: root.album !== null && root.canShowProperties }
    MichiMenuItem {
        text: qsTr("Album Properties")
        icon.name: "info"
        visible: root.album !== null && root.canShowProperties
        onTriggered: library.request_album_properties(root.album.key)
    }
}
