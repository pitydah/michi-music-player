import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiMenu {
    id: root
    property var artist: null
    // M9-R3 CONTEXTUAL RECOVERY (fail-closed): nunca exponer una acción
    // solo porque el Bridge tenga un signal. "Add Artist to Playlist"
    // requiere un consumer productivo compartido (fase R4 lo activa);
    // hasta entonces la capacidad permanece FALSE por defecto.
    property bool canAddToPlaylist: false
    property bool canCreatePlaylist: false

    MichiMenuInfoHeader {
        headline: root.artist ? root.artist.name : ""
        supportingText: root.artist
            ? qsTr("%n album(s) · %n track(s)", "",
                root.artist.albumCount, root.artist.trackCount)
            : ""
        artworkPath: root.artist ? root.artist.artworkPath : ""
        fallbackText: root.artist ? root.artist.name : "A"
        portrait: true
    }
    MichiSeparator { }
    // ── R10 grupos semánticos (V4 §11.3) ─────────────────────────────
    MichiMenuHeader {
        text: qsTr("PLAYBACK")
        visible: root.artist !== null
    }
    MichiMenuItem {
        text: qsTr("Open Artist")
        icon.name: "artist"
        visible: root.artist !== null
        onTriggered: library.select_artist(root.artist.key)
    }
    MichiMenuItem {
        text: qsTr("Add Artist to Queue")
        icon.name: "queue"
        visible: root.artist !== null && library.canQueueTracks
        onTriggered: library.queue_artist(root.artist.key)
    }

    MichiMenuHeader {
        text: qsTr("COLLECTION")
        visible: root.artist !== null && root.canAddToPlaylist
            && library.canAddTracksToPlaylists
    }
    MichiMenuItem {
        text: qsTr("Add Artist to Playlist")
        icon.name: "add"
        visible: root.artist !== null && root.canAddToPlaylist
            && library.canAddTracksToPlaylists
        onTriggered: library.request_artist_playlist_target(root.artist.key)
    }
    MichiMenuItem {
        text: qsTr("Create Playlist from Artist…")
        icon.name: "plus"
        // R4: seam request_new_playlist_for_artist → host (A1) → dialog.
        visible: root.artist !== null && root.canCreatePlaylist
            && library.canAddTracksToPlaylists
        onTriggered: library.request_new_playlist_for_artist(root.artist.key)
    }
}
