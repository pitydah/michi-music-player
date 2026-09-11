import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiMenu {
    id: root
    property var album: null
    // The same menu is used from album cards and from Album Detail.  Cards
    // need Open Album; inside the already-open detail that action is a
    // redundant no-op, so the caller may suppress it without forking IA.
    property bool showOpenAction: true
    // POST-MERGE CONTEXTUAL RECOVERY: never expose an action merely
    // because a backend signal exists. The host must explicitly prove a
    // productive consumer for picker/create/properties flows.
    property bool canAddToPlaylist: false
    property bool canCreatePlaylist: false
    property bool canShowProperties: false

    MichiMenuInfoHeader {
        // Guards sobre el CAMPO (no solo sobre el objeto): un album
        // transitorio sin title/artist no puede emitir
        // "Unable to assign [undefined] to QString" en el header.
        headline: root.album && root.album.title ? root.album.title : ""
        supportingText: root.album && root.album.artist
            ? root.album.artist
                + (root.album.year > 0 ? " · " + root.album.year : "")
            : ""
        artworkPath: root.album && root.album.hasArtwork
            ? root.album.artworkPath : ""
        fallbackText: root.album && root.album.title ? root.album.title : "A"
    }
    MichiSeparator { }
    // ── R10 grupos semánticos (V4 §11.2) ─────────────────────────────
    MichiMenuHeader {
        text: qsTr("PLAYBACK")
        visible: root.album !== null
    }
    MichiMenuItem {
        text: qsTr("Open Album")
        icon.name: "album"
        visible: root.album !== null && root.showOpenAction
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

    MichiMenuHeader {
        text: qsTr("COLLECTION")
        visible: root.album !== null && root.canAddToPlaylist
            && library.canAddTracksToPlaylists
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

    MichiMenuHeader {
        text: qsTr("NAVIGATE")
        visible: root.album !== null && Boolean(root.album.artistKey)
    }
    MichiMenuItem {
        text: qsTr("Go to Artist")
        icon.name: "artist"
        visible: root.album !== null && Boolean(root.album.artistKey)
        onTriggered: library.select_artist(root.album.artistKey)
    }

    MichiMenuHeader {
        text: qsTr("DETAILS")
        visible: root.album !== null && root.canShowProperties
    }
    MichiMenuItem {
        text: qsTr("Album Properties")
        icon.name: "info"
        visible: root.album !== null && root.canShowProperties
        onTriggered: library.request_album_properties(root.album.key)
    }
}
