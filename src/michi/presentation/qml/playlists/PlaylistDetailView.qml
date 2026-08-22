import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

// PlaylistDetailView — PLAYLISTS + playlist_id. Header (back, name, count,
// pin, play), track list with remove/reorder, rename and delete flows.
// Delete requires confirmation; wording never implies file deletion.
Item {
    id: root

    objectName: "playlistDetailView"
    property string playlistId: ""
    signal backRequested()
    signal playRequested()
    signal togglePinRequested()
    // M9-R1J: presentation-intent emitters only — dialogs live in the
    // Shell (ContentHost); the Detail NEVER opens dialogs itself.
    signal renameRequested(string playlistId, string playlistName)
    signal deleteRequested(string playlistId, string playlistName)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)

    readonly property bool _selected: playlists.selectedPlaylistId === root.playlistId

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.md
            MichiIconButton {
                iconName: "back"
                accessibleName: qsTr("Back to All Playlists")
                onClicked: root.backRequested()
            }
            Rectangle {
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64
                radius: MichiRadius.lg
                color: MichiSemanticColors.auroraPurpleSurface
                border.width: 1
                border.color: MichiSemanticColors.auroraPurpleBorder
                MichiIcon {
                    anchors.centerIn: parent
                    name: "playlist"
                    width: 30
                    height: 30
                    iconColor: MichiPalette.auroraCyan
                }
            }
            ColumnLayout {
                spacing: 2
                MichiText {
                    id: titleText
                    text: playlists.selectedPlaylistName
                    role: "section"
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    color: MichiPalette.textPrimary
                }
                MichiText {
                    text: playlists.playlistTracks.length + " tracks"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                }
            }
            Item { Layout.fillWidth: true }
            MichiIconButton {
                iconName: "pin"
                // M9-R1I: pin state derives from the navigated playlist
                // (selectedPlaylistPinned projection) — never playlists[0].
                selected: playlists.selectedPlaylistPinned
                accessibleName: playlists.selectedPlaylistPinned
                    ? qsTr("Unpin playlist") : qsTr("Pin playlist")
                onClicked: root.togglePinRequested()
            }
            MichiButton {
                text: qsTr("Play")
                variant: "primary"
                iconName: "play"
                enabled: playlists.playlistTracks.length > 0
                accessibleName: qsTr("Play playlist")
                onClicked: root.playRequested()
            }
            MichiIconButton {
                iconName: "sliders"
                accessibleName: qsTr("More options")
                onClicked: detailMenu.popup()
            }
        }

        // M9-R1I: only ONE surface owns the body — the track list hides
        // when empty (no hidden ListView consuming layout space) and the
        // EmptyState fills the available height exclusively.
        PlaylistTrackList {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlistTrackRows.length > 0
            rows: playlists.playlistTrackRows
            onRemoveTrackRequested: index => root.removeTrackRequested(index)
            onMoveTrackRequested: (f, t) => root.moveTrackRequested(f, t)
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlistTrackRows.length === 0
            title: qsTr("Empty playlist")
            message: qsTr("Add tracks from your library to start collecting them here.")
            iconName: "playlist"
        }
    }

    MichiMenu {
        id: detailMenu
        MenuItem {
            objectName: "playlistDetailRenameAction"
            text: qsTr("Rename")
            onTriggered: root.renameRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
        MenuItem {
            objectName: "playlistDetailDeleteAction"
            text: qsTr("Delete playlist")
            onTriggered: root.deleteRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
    }

}
