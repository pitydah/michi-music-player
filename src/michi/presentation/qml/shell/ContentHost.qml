import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../playlists"
import "../primitives"
import "../theme"
import "../views"

Item {
    id: root
    property string currentRoute: ""
    property var pendingPlaylistSelection: ({})
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

    function selectionDescription(payload) {
        if (!payload)
            return ""
        if (payload.kind === "album")
            return qsTr("Choose a playlist for this album.")
        if (payload.kind === "artist")
            return qsTr("Choose a playlist for this artist.")
        var count = (payload.trackIds || []).length
        return count === 1
            ? qsTr("Choose a playlist for this track.")
            : qsTr("Choose a playlist for %1 tracks.").arg(count)
    }

    function addSelectionToPlaylist(playlistId, payload) {
        if (!payload)
            return 0
        if (payload.kind === "album")
            return library.add_album_to_playlist(playlistId, payload.albumKey)
        if (payload.kind === "artist")
            return library.add_artist_to_playlist(playlistId, payload.artistKey)
        return library.add_tracks_to_playlist(playlistId, payload.trackIds || [])
    }

    function createPlaylistForSelection(name, payload) {
        if (!payload)
            return ""
        if (payload.kind === "album")
            return library.create_playlist_from_album(name, payload.albumKey)
        if (payload.kind === "artist")
            return library.create_playlist_from_artist(name, payload.artistKey)
        return library.create_playlist_from_tracks(name, payload.trackIds || [])
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
                // Incoming page is interactive immediately; outgoing page
                // remains renderable only while its fade still has alpha.
                visible: !root._playlistDetail || opacity > 0
                enabled: !root._playlistDetail
                opacity: root._playlistDetail ? 0 : 1
                z: root._playlistDetail ? 0 : 1
                transform: Translate {
                    y: root._playlistDetail && !MichiAccessibility.reducedMotion
                        ? -MichiSpacing.sm : 0
                    Behavior on y {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.page; easing.type: MichiMotion.outCubic }
                    }
                }
                Behavior on opacity {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.page; easing.type: MichiMotion.outCubic }
                }
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
                visible: root._playlistDetail || opacity > 0
                enabled: root._playlistDetail
                opacity: root._playlistDetail ? 1 : 0
                z: root._playlistDetail ? 1 : 0
                transform: Translate {
                    y: root._playlistDetail || MichiAccessibility.reducedMotion
                        ? 0 : MichiSpacing.sm
                    Behavior on y {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.page; easing.type: MichiMotion.outCubic }
                    }
                }
                Behavior on opacity {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.page; easing.type: MichiMotion.outCubic }
                }
                playlistId: navigation.playlistId
                onBackRequested: playlists.open_all_playlists()
                onPlayRequested: playlists.play_selected_playlist()
                onShuffleRequested: {
                    if (typeof playback !== "undefined" && playback)
                        playback.shuffle = true
                    playlists.play_selected_playlist()
                }
                onPlayTrackRequested: index => playlists.play_track(index)
                onAddMusicRequested: libraryTrackPicker.begin()
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
                                library.add_tracks_to_playlist(
                                    playlists.selectedPlaylistId, [removed.path])
                            })
                    }
                }
                onMoveTrackRequested: (fromIndex, toIndex) => {
                    playlists.move_track(fromIndex, toIndex)
                }
                onAddToPlaylistRequested: trackId => {
                    library.request_tracks_playlist_target([trackId])
                }
                onGoToAlbumRequested: albumKey => {
                    navigation.navigate("library")
                    library.select_album(albumKey)
                }
                onGoToArtistRequested: artistKey => {
                    navigation.navigate("library")
                    library.select_artist(artistKey)
                }
            }
        }
    }

    LibraryTrackPicker {
        id: libraryTrackPicker
        trackRows: library.songRows
        onTracksRequested: trackIds => {
            var added = library.add_tracks_to_playlist(
                playlists.selectedPlaylistId, trackIds)
            if (added > 0 && typeof window !== "undefined" && window)
                window.showToast(qsTr("Added %1 tracks").arg(added))
        }
    }

    PlaylistTargetPicker {
        id: playlistTargetPicker
        playlistRows: playlists.playlists
        pinnedRows: playlists.pinnedPlaylists
        recentRows: playlists.recentPlaylists
        selectionPayload: root.pendingPlaylistSelection
        selectionDescription: root.selectionDescription(selectionPayload)
        onTargetRequested: (playlistId, playlistName, payload) => {
            var added = root.addSelectionToPlaylist(playlistId, payload)
            if (added > 0 && typeof window !== "undefined" && window)
                window.showToast(qsTr("Added to %1").arg(playlistName))
        }
        onNewPlaylistRequested: payload => selectionCreateDialog.begin(payload)
    }

    SelectionPlaylistCreateDialog {
        id: selectionCreateDialog
        onCreateRequested: (name, payload) => {
            var playlistId = root.createPlaylistForSelection(name, payload)
            complete(playlistId.length > 0)
            if (playlistId.length > 0 && typeof window !== "undefined" && window)
                window.showToast(qsTr("Created playlist and added selection"))
        }
    }

    AlbumPropertiesView { id: albumPropertiesView }

    Connections {
        target: library
        function onPlaylist_target_requested(payload) {
            root.pendingPlaylistSelection = payload
            playlistTargetPicker.open()
        }
        function onNew_playlist_target_requested(payload) {
            selectionCreateDialog.begin(payload)
        }
        function onAlbum_properties_requested(album) {
            albumPropertiesView.inspect(album)
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
