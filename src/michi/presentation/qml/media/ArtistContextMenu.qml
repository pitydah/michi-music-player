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
    // requiere un consumer productivo compartido (PR D instala el host);
    // hasta entonces la capacidad permanece FALSE por defecto.
    property bool canAddToPlaylist: false

    Item {
        implicitWidth: 284
        implicitHeight: 56
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.sm
            anchors.rightMargin: MichiSpacing.sm
            spacing: MichiSpacing.sm
            ArtistPortraitArtwork {
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                sourcePath: root.artist ? root.artist.artworkPath : ""
                fallbackText: root.artist ? root.artist.name : "A"
                requestedSize: 72
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                MichiText {
                    Layout.fillWidth: true
                    text: root.artist ? root.artist.name : ""
                    role: "body"
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: root.artist
                        ? root.artist.albumCount
                            + (root.artist.albumCount === 1 ? " album · " : " albums · ")
                            + root.artist.trackCount
                            + (root.artist.trackCount === 1 ? " track" : " tracks")
                        : ""
                    role: "caption"
                    elide: Text.ElideRight
                }
            }
        }
    }
    MichiSeparator { }
    MichiMenuItem { text: qsTr("Open Artist"); icon.name: "artist"; visible: root.artist !== null; onTriggered: library.select_artist(root.artist.key) }
    MichiMenuItem { text: qsTr("Add Artist to Queue"); icon.name: "queue"; visible: root.artist !== null && library.canQueueTracks; onTriggered: library.queue_artist(root.artist.key) }
    MichiSeparator { visible: root.artist !== null && root.canAddToPlaylist && library.canAddTracksToPlaylists }
    MichiMenuItem {
        text: qsTr("Add Artist to Playlist")
        icon.name: "add"
        visible: root.artist !== null && root.canAddToPlaylist
            && library.canAddTracksToPlaylists
        onTriggered: library.request_artist_playlist_target(root.artist.key)
    }
}
