import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

// PlaylistsView — All Playlists (PLAYLISTS + None). Responsive card grid
// (ListView-style virtualization via GridView), quiet content surfaces,
// deterministic placeholder mosaic. Empty state offers Create.
Item {
    id: root

    objectName: "playlistsView"
    signal createPlaylistRequested()
    signal openPlaylistRequested(string playlistId)
    signal playPlaylistRequested(string playlistId)
    signal pinPlaylistRequested(string playlistId, bool pinned)
    signal renamePlaylistRequested(string playlistId, string playlistName)
    signal deletePlaylistRequested(string playlistId, string playlistName)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.lg
            ColumnLayout {
                spacing: 2
                MichiText {
                    text: qsTr("Playlists")
                    role: "section"
                    color: MichiPalette.textPrimary
                }
                MichiText {
                    text: playlists.playlists.length + " playlists"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                }
            }
            Item { Layout.fillWidth: true }
            MichiButton {
                text: qsTr("New Playlist")
                variant: "primary"
                iconName: "plus"
                accessibleName: qsTr("Create playlist")
                onClicked: root.createPlaylistRequested()
            }
        }

        // Empty state
        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlists.length === 0
            title: qsTr("No playlists yet")
            message: qsTr("Create a playlist to collect tracks from your library.")
            actionText: qsTr("Create Playlist")
            iconName: "playlist"
            onActionRequested: root.createPlaylistRequested()
        }

        // Card grid — virtualized; columns adapt to width. GridView has no
        // spacing property: gaps live in cellWidth/cellHeight (gap = lg).
        GridView {
            id: gridView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlists.length > 0
            clip: true
            cellWidth: Math.max(240, (root.width - MichiSpacing.xl * 2) / Math.max(1, Math.floor((root.width - MichiSpacing.xl) / 264)))
            cellHeight: 216
            model: playlists.playlists
            delegate: PlaylistCard {
                width: gridView.cellWidth - MichiSpacing.lg
                height: gridView.cellHeight - MichiSpacing.lg
                playlistId: modelData.playlistId
                playlistName: modelData.name
                trackCount: modelData.trackCount
                pinned: modelData.pinned
                onOpenRequested: root.openPlaylistRequested(modelData.playlistId)
                onPlayRequested: root.playPlaylistRequested(modelData.playlistId)
                onPinToggled: root.pinPlaylistRequested(modelData.playlistId, !modelData.pinned)
                onRenameRequested: root.renamePlaylistRequested(
                    modelData.playlistId, modelData.name)
                onDeleteRequested: root.deletePlaylistRequested(
                    modelData.playlistId, modelData.name)
            }
        }
    }
}
