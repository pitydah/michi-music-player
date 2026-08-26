import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../playlists"
import "../primitives"
import "../theme"
import "../views"

Item {
    id: root
    property string currentRoute: ""
    signal createPlaylistRequested()

    function routeIndex(route) {
        switch (route) {
        case "now_playing": return 0
        case "library":     return 1
        case "queue":       return 2
        case "settings":    return 3
        case "playlists":   return 4
        default:            return 1
        }
    }

    // PLAYLIST-HIERARCHY-04: detail = PLAYLISTS + playlist_id; All
    // Playlists = PLAYLISTS + None. NavigationState decides the screen;
    // PlaylistsBridge provides content (single navigation truth).
    readonly property bool _playlistDetail: root.currentRoute === "playlists"
        && navigation.playlistId !== ""

    MichiSurface { anchors.fill: parent; level: "content"; radius: MichiRadius.floating }

    StackLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        currentIndex: root.routeIndex(root.currentRoute)

        NowPlayingView { }
        LibraryView { }
        QueueView { }
        SettingsView { }

        // PLAYLISTS route host: All Playlists or Detail by playlist target.
        Item {
            id: playlistsRouteHost
            objectName: "playlistsRouteHost"

            PlaylistsView {
                id: allPlaylistsView
                objectName: "allPlaylistsView"
                anchors.fill: parent
                visible: !root._playlistDetail
                onCreatePlaylistRequested: root.createPlaylistRequested()
                onOpenPlaylistRequested: playlistId => playlists.open_playlist(playlistId)
                onPlayPlaylistRequested: playlistId => playlists.play_playlist(playlistId)
                onPinPlaylistRequested: (playlistId, pinned) => {
                    if (pinned) playlists.pin_playlist(playlistId)
                    else playlists.unpin_playlist(playlistId)
                }
                // M9-R1I: card dialogs use EPHEMERAL action targets — they
                // never touch navigation (no select_playlist, no Detail
                // flash; PLAYLISTS/None stays while renaming/deleting).
                onRenamePlaylistRequested: (playlistId, playlistName) => {
                    renameDialog.targetPlaylistId = playlistId
                    renameDialog.targetPlaylistName = playlistName
                    renameDialog.open()
                }
                onDeletePlaylistRequested: (playlistId, playlistName) => {
                    deleteDialog.targetPlaylistId = playlistId
                    deleteDialog.targetPlaylistName = playlistName
                    deleteDialog.open()
                }
            }

            PlaylistDetailView {
                id: playlistDetail
                objectName: "playlistDetailView"
                anchors.fill: parent
                visible: root._playlistDetail
                playlistId: navigation.playlistId
                onBackRequested: playlists.open_all_playlists()
                onPlayRequested: playlists.play_selected_playlist()
                onShuffleRequested: {
                    if (typeof playback !== "undefined" && playback)
                        playback.shuffle = true
                    playlists.play_selected_playlist()
                }
                onPlayTrackRequested: index => playlists.play_track(index)
                onAddMusicRequested: navigation.navigate("library")
                onTogglePinRequested: {
                    if (playlists.selectedPlaylistPinned)
                        playlists.unpin_playlist(playlists.selectedPlaylistId)
                    else
                        playlists.pin_playlist(playlists.selectedPlaylistId)
                }
                // M9-R1J: the shared dialogs are the canonical interaction
                // boundary — the Detail emits intents; ContentHost routes
                // them into the SAME dialogs used by All Playlists cards.
                onRenameRequested: (playlistId, playlistName) => {
                    renameDialog.targetPlaylistId = playlistId
                    renameDialog.targetPlaylistName = playlistName
                    renameDialog.open()
                }
                onDeleteRequested: (playlistId, playlistName) => {
                    deleteDialog.targetPlaylistId = playlistId
                    deleteDialog.targetPlaylistName = playlistName
                    deleteDialog.open()
                }
                onRemoveTrackRequested: index => {
                    var removed = playlists.playlistTracks[index]
                    playlists.remove_track(index)
                    if (removed && removed.path) {
                        // Phase 4 undo: re-add the removed track by path.
                        window.showToastWithAction(
                            qsTr("Removed from playlist"), qsTr("Undo"),
                            function() {
                                playlists.add_track_to_playlist(
                                    playlists.selectedPlaylistId, removed.path)
                            })
                    }
                }
                onMoveTrackRequested: (fromIndex, toIndex) => {
                    playlists.move_track(fromIndex, toIndex)
                }
            }
        }
    }

    // Shared rename dialog — ephemeral action targets for All Playlists
    // cards; in Detail the target is the navigated playlist.
    MichiDialog {
        id: renameDialog
        objectName: "renamePlaylistDialog"
        title: qsTr("Rename playlist")
        width: 420
        property string errorText: ""
        property string targetPlaylistId: ""
        property string targetPlaylistName: ""
        standardButtons: Dialog.NoButton

        function showError(message) {
            renameDialog.errorText = message
        }

        contentItem: ColumnLayout {
            spacing: MichiSpacing.md
            MichiTextField {
                id: renameField
                objectName: "playlistRenameField"
                Layout.fillWidth: true
                placeholderText: qsTr("Playlist name")
                text: renameDialog.targetPlaylistName
                onAccepted: renameDialog._submit()
            }
            MichiText {
                visible: renameDialog.errorText !== ""
                text: renameDialog.errorText
                role: "technical"
                technical: true
                color: MichiPalette.error
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cancel")
                    variant: "ghost"
                    onClicked: renameDialog.close()
                }
                MichiButton {
                    text: qsTr("Rename")
                    variant: "primary"
                    onClicked: renameDialog._submit()
                }
            }
        }
        function _submit() {
            var name = renameField.text.trim()
            if (name === "") {
                renameDialog.errorText = qsTr("Playlist name must not be empty")
                return
            }
            // M9-R1I explicit contract: only close on real success.
            if (playlists.rename_playlist(renameDialog.targetPlaylistId, name)) {
                renameDialog.close()
            } else {
                renameDialog.errorText = qsTr("A playlist with that name already exists.")
            }
        }
        onOpened: {
            renameField.text = renameDialog.targetPlaylistName
            renameDialog.errorText = ""
            renameField.forceActiveFocus()
        }
    }

    // Shared delete dialog — same ephemeral target model.
    MichiDialog {
        id: deleteDialog
        objectName: "deletePlaylistDialog"
        title: qsTr("Delete \"%1\"?").arg(deleteDialog.targetPlaylistName)
        width: 440
        property string targetPlaylistId: ""
        property string targetPlaylistName: ""
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: MichiSpacing.md
            MichiText {
                text: qsTr("The playlist will be removed. Music files will remain in your library.")
                role: "secondary"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                color: MichiPalette.textSecondary
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cancel")
                    variant: "ghost"
                    onClicked: deleteDialog.close()
                }
                MichiButton {
                    text: qsTr("Delete")
                    variant: "danger"
                    onClicked: deleteDialog._confirm()
                }
            }
        }
        function _confirm() {
            playlists.delete_playlist(deleteDialog.targetPlaylistId)
            deleteDialog.close()
        }
    }
}
