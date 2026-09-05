import QtQuick
import QtQuick.Layouts
import "../media"
import "../playlists"
import "../theme"

// LIBRARY CONTEXT ACTION HOST (A1) — router/consumer de Presentation.
//
// Escucha los intents del LibraryBridge y los convierte en workflows
// productivos reutilizando los componentes premium existentes. Es un
// CONSUMER: no persiste, no resuelve TrackId, no toca filesystem, no
// replica Domain, no es un segundo backend.
//
// Payloads canónicos (Appendix B):
//   tracks  → {"kind":"tracks",  "trackIds":[...]}   — TrackId identidad
//   album   → {"kind":"album",   "albumKey":"..."}
//   artist  → {"kind":"artist",  "artistKey":"..."}
//
// Rechaza payloads inválidos sin abrir nada (fail-closed, cero
// visible→click→nada).
Item {
    id: root
    objectName: "libraryContextActionHost"

    // Feedback observable: en la app se enruta a window.showToast; la
    // señal queda disponible para harness de runtime.
    signal feedbackRequested(string text, string tone)

    PlaylistTargetPicker {
        id: targetPicker
        objectName: "libraryContextTargetPicker"
        playlistRows: typeof playlists !== "undefined" && playlists
            ? playlists.playlists : []
        pinnedRows: typeof playlists !== "undefined" && playlists
            ? playlists.pinnedPlaylists : []
        recentRows: typeof playlists !== "undefined" && playlists
            ? playlists.recentPlaylists : []
        onTargetRequested: (playlistId, playlistName, payload) =>
            root._addSelection(playlistId, playlistName, payload)
        onNewPlaylistRequested: payload => root.openNewPlaylist(payload)
    }

    SelectionPlaylistCreateDialog {
        id: createDialog
        objectName: "libraryContextCreateDialog"
        onCreateRequested: (name, payload) => root._createPlaylist(name, payload)
    }

    TrackPropertiesView {
        id: trackProperties
        objectName: "libraryContextTrackProperties"
    }

    AlbumPropertiesView {
        id: albumProperties
        objectName: "libraryContextAlbumProperties"
    }

    // ── API pública del router ───────────────────────────────────────────

    function openPlaylistTarget(payload) {
        if (!root._validSelection(payload)) {
            root._toast(qsTr("Invalid selection"), "error")
            return
        }
        targetPicker.selectionPayload = payload
        targetPicker.selectionDescription = root._selectionDescription(payload)
        targetPicker.open()
    }

    function openNewPlaylist(payload) {
        if (!root._validSelection(payload)) {
            root._toast(qsTr("Invalid selection"), "error")
            return
        }
        createDialog.begin(payload)
    }

    function inspectTrack(row) {
        if (!row)
            return
        trackProperties.inspect(row)
    }

    function inspectAlbum(snapshot) {
        if (!snapshot)
            return
        albumProperties.inspect(snapshot)
    }

    // ── dispatch ─────────────────────────────────────────────────────────

    function _addSelection(playlistId, playlistName, payload) {
        if (!root._validSelection(payload)) {
            root._toast(qsTr("Invalid selection"), "error")
            return
        }
        // Los slots del Bridge son la autoridad: el resultado observable
        // es el del backend (nunca éxito simulado antes del resultado).
        var added = 0
        if (payload.kind === "tracks")
            added = library.add_tracks_to_playlist(playlistId, payload.trackIds)
        else if (payload.kind === "album")
            added = library.add_album_to_playlist(playlistId, payload.albumKey)
        else if (payload.kind === "artist")
            added = library.add_artist_to_playlist(playlistId, payload.artistKey)
        else
            return
        if (added > 0)
            root._toast(qsTr("Added to %1").arg(playlistName), "success")
        else
            root._toast(qsTr("Already in %1").arg(playlistName), "info")
    }

    function _createPlaylist(name, payload) {
        if (!root._validSelection(payload)) {
            createDialog.complete(false)
            return
        }
        var playlistId = ""
        if (payload.kind === "tracks")
            playlistId = library.create_playlist_from_tracks(name, payload.trackIds)
        else if (payload.kind === "album")
            playlistId = library.create_playlist_from_album(name, payload.albumKey)
        else if (payload.kind === "artist")
            playlistId = library.create_playlist_from_artist(name, payload.artistKey)
        if (playlistId !== "") {
            createDialog.complete(true)
            root._toast(qsTr("Created %1").arg(name), "success")
        } else {
            // Falla real (nombre duplicado/inválido): el diálogo permanece
            // abierto con el error inline — nunca fake success.
            createDialog.complete(false)
        }
    }

    // ── helpers ──────────────────────────────────────────────────────────

    function _validSelection(payload) {
        if (!payload)
            return false
        if (payload.kind === "tracks") {
            // Los trackIds llegan del Bridge como QVariantList: en JS NO
            // pasan Array.isArray (verificado en runtime) — validar por
            // length + índices, nunca por Array.isArray.
            var ids = payload.trackIds
            if (!ids || typeof ids.length !== "number" || ids.length === 0)
                return false
            for (var index = 0; index < ids.length; ++index) {
                if (typeof ids[index] !== "string" || ids[index].length === 0)
                    return false
            }
            return true
        }
        if (payload.kind === "album")
            return typeof payload.albumKey === "string"
                && payload.albumKey.length > 0
        if (payload.kind === "artist")
            return typeof payload.artistKey === "string"
                && payload.artistKey.length > 0
        return false
    }

    function _selectionDescription(payload) {
        if (payload.kind === "tracks")
            return qsTr("%n track(s) selected", "", payload.trackIds.length)
        if (payload.kind === "album")
            return qsTr("Album tracks selected")
        return qsTr("Artist tracks selected")
    }

    function _toast(text, tone) {
        root.feedbackRequested(text, tone || "info")
        if (typeof window !== "undefined" && window
                && typeof window.showToast === "function")
            window.showToast(text, tone || "info")
    }
}
