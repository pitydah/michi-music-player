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
                onBackRequested: {
                    // PL-FINAL-A02: salir del detalle limpia la búsqueda
                    // local (estado transiente).
                    playlists.set_playlist_search_query("")
                    playlists.open_all_playlists()
                }
                onPlayRequested: playlists.play_selected_playlist()
                onShuffleRequested: {
                    // PL-10-FINAL-06: defensivo — sin tracks reproducibles
                    // el shuffle no toca el motor ni el playback state.
                    if (!playlists || playlists.playlistAvailableTrackCount <= 0)
                        return
                    if (typeof playback !== "undefined" && playback)
                        playback.shuffle = true
                    playlists.play_selected_playlist()
                }
                onPlayTrackRequested: index => playlists.play_playlist_track(index)
                onAddMusicRequested: {
                    // PL-FINAL-13: Add Tracks es un workflow REAL dentro del
                    // contexto del playlist (picker modal) — ya no navega
                    // vagamente a Library abandonando el contexto.
                    root.trackPicker.playlistId = playlists.selectedPlaylistId
                    root.trackPicker.open()
                }
                onEditDescriptionRequested: (playlistId, description) => {
                    descriptionDialog.targetPlaylistId = playlistId
                    descriptionField.text = description
                    descriptionDialog.open()
                }
                onRemoveTracksRequested: paths => {
                    // PL-10-FINAL-05: batch remove por PATH IDENTITY con
                    // resultado estructurado TRUTHFUL — el toast usa el
                    // conteo REAL de removidos, nunca la longitud del
                    // intent (paths ya desaparecidos = missingCount).
                    var result = playlists.remove_tracks_by_paths(paths)
                    if (result.status === "removed") {
                        playlistDetail.checkedTrackPaths = []
                        playlistDetail.shiftAnchorPath = ""
                        playlistDetail.selectionMode = false
                        var message = qsTr("%n tracks removed", "",
                            result.removedCount)
                        if (result.missingCount > 0)
                            message += qsTr(" · %n no longer present", "",
                                result.missingCount)
                        window.showToast(message)
                    }
                    // "persistence_failed": connector reports exactly once.
                }
                onTogglePinRequested: {
                    // R4-08: el feedback se deriva del COMMAND INTENT
                    // confirmado, nunca del post-state (que ya cambió).
                    var shouldPin = !playlists.selectedPlaylistPinned
                    var playlistId = playlists.selectedPlaylistId
                    var playlistName = playlists.selectedPlaylistName
                    var result = shouldPin
                        ? playlists.pin_playlist(playlistId)
                        : playlists.unpin_playlist(playlistId)
                    if (result === "updated")
                        window.showToast(shouldPin
                            ? qsTr("Pinned %1").arg(playlistName)
                            : qsTr("Unpinned %1").arg(playlistName))
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
                                    // PLAYLISTS IDENTITY RECOVERY (2.1):
                                    // el Undo restaura la REFERENCIA congelada
                                    // (trackId + path factual) — tras una
                                    // relocation el track recupera su MISMA
                                    // identidad, nunca un miembro path-only.
                                    if (removed.trackId) {
                                        playlists.insert_track_reference(
                                            removedPlaylistId, removedIndex,
                                            removed.trackId, removed.path)
                                    } else {
                                        playlists.insert_track(
                                            removedPlaylistId, removedIndex,
                                            removed.path)
                                    }
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
        // R4-04: el editor parte del PERSISTED INTENT; el effective es
        // solo preview. Un hero image missing nunca se convierte en Auto
        // implícitamente.
        persistedHeroMode: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.persistedHeroMode || "auto"
        persistedHeroImagePath: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.persistedHeroImagePath || ""
        effectiveHeroMode: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.effectiveHeroMode || "auto"
        effectiveHeroImagePath: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.effectiveHeroImagePath || ""
        heroImageMissing: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.heroImageMissing || false
        heroSolidColor: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.heroSolidColor || MichiPalette.playlistHeroTopHex
        heroGradientColors: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.heroGradientColors || [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex]
        heroGradientAngle: {
            var row = root._appearanceRowFor(root.appearanceTargetPlaylistId)
            return row && row.heroGradientAngle !== undefined
                ? row.heroGradientAngle : 135
        }
        autoHeroColors: root._appearanceRowFor(root.appearanceTargetPlaylistId)?.autoHeroColors || [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex, MichiPalette.playlistHeroBottomHex]
        // PL-FINAL-09: focal persistido (draft del editor).
        persistedHeroFocalX: {
            var row = root._appearanceRowFor(root.appearanceTargetPlaylistId)
            return row && row.heroFocalX !== undefined ? row.heroFocalX : 0.5
        }
        persistedHeroFocalY: {
            var row = root._appearanceRowFor(root.appearanceTargetPlaylistId)
            return row && row.heroFocalY !== undefined ? row.heroFocalY : 0.5
        }
    }

    // PL-FINAL-13: Add Tracks picker — batch add real, contexto del
    // playlist preservado.
    PlaylistTrackPicker {
        id: trackPicker
        objectName: "playlistTrackPicker"
        playlistId: ""
        // PL-FINAL-A08: membership CANÓNICA — nunca la proyección filtrada
        // por la búsqueda local del Detail.
        presentPaths: playlists.selectedPlaylistTrackPaths || []
        // 2.1: 'already present' por TrackId (relocation-safe).
        presentTrackIds: playlists.selectedPlaylistTrackIds || []
        onAddCompleted: (added, alreadyPresent) => {
            var message = qsTr("%n tracks added", "", added)
            if (alreadyPresent > 0)
                message += qsTr(" · %n already in playlist", "", alreadyPresent)
            window.showToast(message)
        }
    }

    // PL-FINAL-05: real playlist description edit (compact dialog).
    MichiDialog {
        id: descriptionDialog
        objectName: "playlistDescriptionDialog"
        title: qsTr("Edit description")
        width: 480
        property string targetPlaylistId: ""
        property string errorText: ""
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: MichiSpacing.md
            MichiText {
                text: qsTr("Describe this playlist — shown in its header.")
                role: "secondary"
                color: MichiPalette.textSecondary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 110
                placeholderText: qsTr("Optional description")
                wrapMode: Text.WordWrap
                color: MichiPalette.textPrimary
                placeholderTextColor: MichiPalette.textMuted
                selectionColor: MichiSemanticColors.surfaceSelected
                selectedTextColor: MichiPalette.textPrimary
                background: Rectangle {
                    radius: MichiRadius.md
                    color: MichiSemanticColors.controlSurface
                    border.width: 1
                    border.color: descriptionField.activeFocus
                        ? MichiSemanticColors.borderStrong
                        : MichiSemanticColors.borderSubtle
                }
                Accessible.name: qsTr("Playlist description")
            }
            MichiText {
                visible: descriptionDialog.errorText !== ""
                text: descriptionDialog.errorText
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
                    onClicked: descriptionDialog.close()
                }
                MichiButton {
                    text: qsTr("Save")
                    variant: "primary"
                    onClicked: descriptionDialog._save()
                }
            }
        }
        function _save() {
            var result = playlists.set_playlist_description(
                descriptionDialog.targetPlaylistId, descriptionField.text)
            if (result === "updated" || result === "no_change") {
                descriptionDialog.errorText = ""
                descriptionDialog.close()
            } else if (result === "invalid") {
                descriptionDialog.errorText = qsTr(
                    "Description must be at most 1000 characters.")
            }
            // "persistence_failed": connector reports exactly once.
        }
        onOpened: {
            descriptionDialog.errorText = ""
            descriptionField.forceActiveFocus()
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
            if (operationCode === "recent")
                // R5-08: la acción PRIMARIA (abrir) SÍ tuvo éxito — solo
                // falló la metadata secundaria.
                message = qsTr("Playlist opened, but Recent wasn't saved")
            else if (operationCode === "create")
                message = qsTr("Could not create playlist")
            else if (operationCode === "rename")
                message = qsTr("Could not rename playlist")
            else if (operationCode === "delete")
                message = qsTr("Could not delete playlist")
            else if (operationCode === "pin" || operationCode === "unpin")
                message = qsTr("Could not update pin state")
            else if (operationCode === "cover" || operationCode === "hero"
                || operationCode === "appearance")
                message = qsTr("Could not update appearance")
            else if (operationCode === "description")
                message = qsTr("Could not save description")
            else if (operationCode === "add_tracks")
                message = qsTr("Could not add tracks")
            else if (operationCode === "remove_track" || operationCode === "remove_tracks")
                message = qsTr("Could not remove tracks")
            else if (operationCode === "move_track")
                message = qsTr("Could not reorder tracks")
            else if (operationCode === "insert_track")
                message = qsTr("Could not restore track")
            window.showToast(message)
        }
    }
}
