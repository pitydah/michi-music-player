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

    // R3-04: el alias evita el module-import collision ("../playlists")
    // para el Connections de persistence failures.
    readonly property var playlistsBridge: playlists

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
                    var result = pinned
                        ? playlists.pin_playlist(playlistId)
                        : playlists.unpin_playlist(playlistId)
                    if (result === "updated")
                        window.showToast(pinned
                            ? qsTr("Pinned %1").arg(playlistName)
                            : qsTr("Unpinned %1").arg(playlistName))
                    // "persistence_failed": connector reports exactly once.
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
                    var result = playlists.selectedPlaylistPinned
                        ? playlists.unpin_playlist(playlists.selectedPlaylistId)
                        : playlists.pin_playlist(playlists.selectedPlaylistId)
                    if (result === "updated")
                        window.showToast(playlists.selectedPlaylistPinned
                            ? qsTr("Unpinned %1").arg(playlists.selectedPlaylistName)
                            : qsTr("Pinned %1").arg(playlists.selectedPlaylistName))
                }
                // M9-R1J: the shared dialogs are the canonical interaction
                // boundary — the Detail emits intents; ContentHost routes
                // them into the SAME dialogs used by All Playlists cards.
                onCustomizeAppearanceRequested: playlistId => {
                    // R3-06: el panel ÚNICO abre con la playlist objetivo.
                    root.appearanceTargetPlaylistId = playlistId
                    root._openAppearancePanel()
                }
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
                    // R3-04: the Undo toast appears ONLY on "removed"; a
                    // persistence failure is reported EXACTLY ONCE by the
                    // persistence connector (no second local toast).
                    var result = playlists.remove_track(index)
                    if (result === "removed") {
                        if (removed && removed.path) {
                            window.showToastWithAction(
                                qsTr("Removed from playlist"), qsTr("Undo"),
                                function() {
                                    playlists.insert_track(
                                        removedPlaylistId, removedIndex, removed.path)
                                })
                        }
                    } else if (result === "invalid_index") {
                        // safe degradation: nothing changed
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
            // R3-04: only close on durable success; logical failures show
            // their specific inline error; persistence failures are
            // reported EXACTLY ONCE by the persistence Connections.
            var result = playlists.rename_playlist(renameDialog.targetPlaylistId, name)
            if (result === "renamed" || result === "no_change") {
                renameDialog.close()
            } else if (result === "conflict") {
                renameDialog.errorText = qsTr("A playlist with that name already exists.")
            } else if (result === "invalid") {
                renameDialog.errorText = qsTr("Playlist name must not be empty")
            }
        }
        onOpened: {
            renameField.text = renameDialog.targetPlaylistName
            renameDialog.errorText = ""
            renameField.forceActiveFocus()
        }
    }

    // R3-06: UN SOLO PlaylistAppearancePanel (como Rename/Delete).
    // Overview y Detail emiten customizeAppearanceRequested(playlistId).
    property string appearanceTargetPlaylistId: ""

    function _appearanceRowFor(playlistId) {
        if (!playlistId || !playlists) return null
        var rows = playlists.playlists || []
        for (var i = 0; i < rows.length; ++i) {
            if (rows[i].playlistId === playlistId) return rows[i]
        }
        return null
    }

    function _openAppearancePanel() {
        // Si el target desapareció, cerrar de forma segura.
        if (!root._appearanceRowFor(root.appearanceTargetPlaylistId)) {
            appearancePanel.close()
            return
        }
        appearancePanel.openForPlaylist()
    }

    PlaylistAppearancePanel {
        id: appearancePanel
        playlistId: root.appearanceTargetPlaylistId
        playlistName: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.name || ""
        customCoverPath: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.effectiveCustomCoverPath || ""
        coverAssetMissing: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.coverAssetMissing || false
        mosaicArtworkPaths: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.mosaicArtworkPaths || []
        heroMode: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.effectiveHeroMode || "auto"
        heroImageMissing: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.heroImageMissing || false
        heroSolidColor: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.heroSolidColor || MichiPalette.playlistHeroTopHex
        heroGradientColors: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.heroGradientColors || [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex]
        heroGradientAngle: {
            var row = root._appearanceRowFor(root.appearanceTargetPlaylistId)
            return row && row.heroGradientAngle !== undefined
                ? row.heroGradientAngle : 135
        }
        heroImagePath: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.effectiveHeroImagePath || ""
        autoHeroColors: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.autoHeroColors || [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex, MichiPalette.playlistHeroBottomHex]
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
            // R3-04: the dialog closes ONLY on "deleted"; persistence
            // failure is reported EXACTLY ONCE by the connector.
            if (playlists.delete_playlist(deleteDialog.targetPlaylistId) === "deleted")
                deleteDialog.close()
        }
    }

    // R3-04: ONE authority for durable-write failures. The Connections
    // uses the local alias (never the raw `playlists` name — the module
    // import would shadow it). The caller NEVER shows a second local
    // error for a persistence failure.
    Connections {
        target: root.playlistsBridge
        function onPersistenceFailed(operationCode) {
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
            window.showToast(message)
        }
    }
}
