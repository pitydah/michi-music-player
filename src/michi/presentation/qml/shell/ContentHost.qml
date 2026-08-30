import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../patterns"
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
                onPinPlaylistRequested: (playlistId, pinned, playlistName) => {
                    var ok = pinned
                        ? playlists.pin_playlist(playlistId)
                        : playlists.unpin_playlist(playlistId)
                    if (ok)
                        window.showToast(pinned
                            ? qsTr("Pinned %1").arg(playlistName)
                            : qsTr("Unpinned %1").arg(playlistName))
                    else
                        window.showToast(qsTr("Could not pin playlist"))
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
                onPlayTrackRequested: index => playlists.play_playlist_track(index)
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
                    // P0-01: FROZEN provenance captured AT REMOVAL TIME — the
                    // Undo callback must never consult the current selection.
                    var removed = playlists.playlistTracks[index]
                    var removedPlaylistId = playlists.selectedPlaylistId
                    var removedIndex = index
                    // R2 P1-12: the Undo toast appears ONLY when the removal
                    // was durably committed.
                    if (playlists.remove_track(index)) {
                        if (removed && removed.path) {
                            window.showToastWithAction(
                                qsTr("Removed from playlist"), qsTr("Undo"),
                                function() {
                                    playlists.insert_track(
                                        removedPlaylistId, removedIndex, removed.path)
                                })
                        }
                    } else {
                        window.showToast(qsTr("Could not remove track"))
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
            // R2 P1-05/P1-12: the dialog closes ONLY when the compound
            // delete was durably committed.
            if (playlists.delete_playlist(deleteDialog.targetPlaylistId)) {
                deleteDialog.close()
            } else {
                window.showToast(qsTr("Could not delete playlist"))
            }
        }
    }

    // R2 P1-05: presentation-safe persistence failure — stable operation
    // code from the bridge, human text here (qsTr). The connector lives in
    // its own component (no `playlists` module-import collision).
    PersistFailureConnector {
        failureMessageFor: function(operationCode) {
            var message = qsTr("Could not save changes")
            if (operationCode === "create")
                message = qsTr("Could not create playlist")
            else if (operationCode === "rename")
                message = qsTr("Could not rename playlist")
            else if (operationCode === "delete")
                message = qsTr("Could not delete playlist")
            else if (operationCode === "pin" || operationCode === "unpin")
                message = qsTr("Could not update pin state")
            else if (operationCode === "cover" || operationCode === "hero")
                message = qsTr("Could not update appearance")
            else if (operationCode === "add_tracks")
                message = qsTr("Could not add tracks")
            else if (operationCode === "remove_track")
                message = qsTr("Could not remove track")
            else if (operationCode === "move_track")
                message = qsTr("Could not reorder tracks")
            else if (operationCode === "insert_track")
                message = qsTr("Could not restore track")
            return message
        }
        notify: function(text) { window.showToast(text) }
    }
}
