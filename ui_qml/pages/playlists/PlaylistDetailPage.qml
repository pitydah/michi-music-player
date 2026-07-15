import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string playlistTitle: ""
    property int playlistId: -1
    property string playlistDescription: ""
    property string playlistCover: ""
    property int trackCount: 0
    property var bridge: null
    property var tracks: []
    property bool _confirmDelete: false
    property string _renameText: ""
    property string _errorMsg: ""
    property string _state: "LOADING"

    signal backRequested()

    function loadPlaylist(pid, title) {
        root.playlistId = pid
        root.playlistTitle = title
        root._confirmDelete = false
        root._state = "LOADING"
        root._errorMsg = ""
        trackListRef.playlistId = pid
        trackListRef.bridge = root.bridge
        var result = trackListRef.refresh()
        root.tracks = trackListRef.tracks || []
        root.trackCount = root.tracks.length
        var plData = null
        if (root.bridge && root.bridge.playlists) {
            for (var i = 0; i < root.bridge.playlists.length; i++) {
                if (root.bridge.playlists[i].id === pid) {
                    plData = root.bridge.playlists[i]
                    break
                }
            }
        }
        if (plData) {
            root.playlistDescription = plData.description || ""
            root.playlistCover = plData.cover_key || ""
        }
        root._state = root.tracks.length > 0 ? "READY" : "EMPTY"
    }

    function playAll() {
        if (root.bridge && typeof root.bridge.playPlaylist !== "undefined" && root.playlistId >= 0)
            root.bridge.playPlaylist(root.playlistId)
    }

    function shuffleAll() {
        if (root.bridge && typeof root.bridge.playPlaylist !== "undefined" && root.playlistId >= 0)
            root.bridge.playPlaylist(root.playlistId)
    }

    function renamePlaylist(name) {
        if (name === "") {
            root._errorMsg = "El nombre no puede estar vacío."
            return false
        }
        if (root.bridge && typeof root.bridge.renamePlaylist !== "undefined" && root.playlistId >= 0) {
            var result = root.bridge.renamePlaylist(root.playlistId, name)
            if (result && !result.ok) {
                root._errorMsg = result.error || "Error al renombrar."
                return false
            }
            root.playlistTitle = name
            root._errorMsg = ""
            return true
        }
        return false
    }

    function deletePlaylist() {
        if (root.bridge && typeof root.bridge.deletePlaylist !== "undefined" && root.playlistId >= 0) {
            root.bridge.deletePlaylist(root.playlistId)
            root.backRequested()
        }
    }

    function missingTrackCount() {
        var count = 0
        for (var i = 0; i < root.tracks.length; i++) {
            if (root.tracks[i].missing) count++
        }
        return count
    }

    objectName: "playlist.detailPage"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Detalle de playlist"
    Accessible.description: "Detalle de la playlist " + root.playlistTitle

    Keys.onEscapePressed: {
        if (editorDialog.opened) editorDialog.close()
        else if (exportDialog.opened) exportDialog.close()
        else root.backRequested()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        focus: true
        objectName: "playlist.detail.flickable"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                objectName: "playlist.detail.header"

                MichiButton {
                    text: "\u2190 Volver"
                    variant: "ghost"
                    onClicked: root.backRequested()
                    objectName: "playlist.detail.backBtn"
                    Accessible.name: "Volver a lista de playlists"
                    KeyNavigation.tab: playBtn
                }

                Text {
                    text: root.playlistTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    Accessible.role: Accessible.Heading
                    Accessible.name: root.playlistTitle
                }

                StatusBadge {
                    text: root.trackCount + " canciones"
                    kind: "info"
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: "playlist.detail.trackCount"
                }

                StatusBadge {
                    text: root.missingTrackCount() + " faltantes"
                    kind: "warning"
                    visible: root.missingTrackCount() > 0
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: "playlist.detail.missingIndicator"
                    Accessible.name: root.missingTrackCount() + " pistas faltantes"
                }
            }

            Text {
                text: root.playlistDescription
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.playlistDescription !== ""
                wrapMode: Text.WordWrap
                width: parent.width * 0.6
            }

            Row {
                spacing: MichiTheme.spacing.sm
                objectName: "playlist.detail.toolbar"

                MichiButton {
                    id: playBtn
                    text: "Reproducir"
                    variant: "primary"
                    onClicked: root.playAll()
                    objectName: "playlist.detail.playAll"
                    Accessible.name: "Reproducir toda la playlist"
                    KeyNavigation.tab: shuffleBtn
                    KeyNavigation.backtab: column.children[0].children[0]
                }
                MichiButton {
                    id: shuffleBtn
                    text: "Aleatorio"
                    variant: "secondary"
                    onClicked: root.shuffleAll()
                    objectName: "playlist.detail.shuffle"
                    Accessible.name: "Reproducir en modo aleatorio"
                    KeyNavigation.tab: addTracksBtn
                    KeyNavigation.backtab: playBtn
                }
                MichiButton {
                    id: addTracksBtn
                    text: "Agregar canciones"
                    variant: "secondary"
                    onClicked: {
                        if (root.bridge && root.bridge.selectionContext &&
                            typeof root.bridge.selectionContext.selectAllLoaded !== "undefined") {
                            root._errorMsg = "Selecciona canciones desde la biblioteca y usa 'Agregar a playlist'"
                        }
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigateWithParams("library", {addToPlaylist: root.playlistId})
                    }
                    objectName: "playlist.detail.addTracks"
                    Accessible.name: "Agregar canciones a la playlist"
                    KeyNavigation.tab: editorBtn
                    KeyNavigation.backtab: shuffleBtn
                }
                MichiButton {
                    id: editorBtn
                    text: "Editar"
                    variant: "ghost"
                    onClicked: {
                        editorDialog.playlistId = root.playlistId
                        editorDialog.playlistName = root.playlistTitle
                        editorDialog.playlistDescription = root.playlistDescription
                        editorDialog.open()
                    }
                    objectName: "playlist.detail.edit"
                    Accessible.name: "Editar metadatos de la playlist"
                    KeyNavigation.tab: duplicateBtn
                    KeyNavigation.backtab: addTracksBtn
                }
                MichiButton {
                    id: duplicateBtn
                    text: "Duplicar"
                    variant: "ghost"
                    onClicked: {
                        if (root.bridge && typeof root.bridge.duplicatePlaylist !== "undefined" && root.playlistId >= 0)
                            root.bridge.duplicatePlaylist(root.playlistId)
                    }
                    objectName: "playlist.detail.duplicate"
                    Accessible.name: "Duplicar playlist"
                    KeyNavigation.tab: exportBtn
                    KeyNavigation.backtab: editorBtn
                }
                MichiButton {
                    id: exportBtn
                    text: "Exportar M3U"
                    variant: "ghost"
                    onClicked: exportDialog.open()
                    objectName: "playlist.detail.export"
                    Accessible.name: "Exportar playlist como M3U"
                    KeyNavigation.tab: deleteBtn
                    KeyNavigation.backtab: duplicateBtn
                }
                MichiButton {
                    id: deleteBtn
                    text: root._confirmDelete ? "Confirmar" : "Eliminar"
                    variant: root._confirmDelete ? "danger" : "ghost"
                    onClicked: {
                        if (!root._confirmDelete) { root._confirmDelete = true }
                        else { root.deletePlaylist() }
                    }
                    objectName: "playlist.detail.delete"
                    Accessible.name: root._confirmDelete ? "Confirmar eliminación" : "Eliminar playlist"
                    Accessible.description: root._confirmDelete ? "Pulsa nuevamente para confirmar" : "Elimina la playlist permanentemente"
                    KeyNavigation.tab: cancelDeleteBtn
                    KeyNavigation.backtab: exportBtn
                }
                MichiButton {
                    id: cancelDeleteBtn
                    text: "Cancelar"
                    variant: "ghost"
                    visible: root._confirmDelete
                    onClicked: root._confirmDelete = false
                    objectName: "playlist.detail.cancelDelete"
                    Accessible.name: "Cancelar eliminación"
                    KeyNavigation.backtab: deleteBtn
                }
            }

            LoadingState {
                width: parent.width
                height: 200
                visible: root._state === "LOADING"
                title: "Cargando playlist"
                objectName: "playlist.detail.loading"
            }

            EmptyState {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root._state === "EMPTY"
                title: "Playlist vacía"
                subtitle: "Agrega canciones desde la biblioteca para empezar."
                iconText: "\uD83C\uDFB6"
                actionText: "Agregar canciones"
                showAction: true
                objectName: "playlist.detail.empty"
                onActionClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigateWithParams("library", {addToPlaylist: root.playlistId})
                }
            }

            PlaylistTrackList {
                id: trackListRef
                width: parent.width
                height: 400
                visible: root._state === "READY"
                bridge: root.bridge
                playlistId: root.playlistId
                tracks: root.tracks
                objectName: "playlist.detail.trackList"
                onPlayRequested: function(index) {
                    if (root.bridge && typeof root.bridge.playPlaylistFromIndex !== "undefined")
                        root.bridge.playPlaylistFromIndex(root.playlistId, index)
                }
                onRemoveRequested: function(trackId, index) {
                    root.tracks.splice(index, 1)
                    root.trackCount = root.tracks.length
                    if (root.tracks.length === 0) root._state = "EMPTY"
                }
                onMoveUpRequested: function(index) {
                    if (index <= 0) return
                    if (root.bridge && typeof root.bridge.reorderTrack !== "undefined") {
                        var result = root.bridge.reorderTrack(root.playlistId, index, index - 1)
                        if (result && result.ok) {
                            var item = root.tracks[index]
                            root.tracks.splice(index, 1)
                            root.tracks.splice(index - 1, 0, item)
                        }
                    }
                }
                onMoveDownRequested: function(index) {
                    if (index >= root.tracks.length - 1) return
                    if (root.bridge && typeof root.bridge.reorderTrack !== "undefined") {
                        var result = root.bridge.reorderTrack(root.playlistId, index, index + 1)
                        if (result && result.ok) {
                            var item = root.tracks[index]
                            root.tracks.splice(index, 1)
                            root.tracks.splice(index + 1, 0, item)
                        }
                    }
                }
            }

            Text {
                text: root._errorMsg
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
    }

    PlaylistEditorDialog {
        id: editorDialog
        bridge: root.bridge
        playlistId: root.playlistId
        playlistName: root.playlistTitle
        playlistDescription: root.playlistDescription
        objectName: "playlist.detail.editorDialog"
        onSaved: {
            root.playlistTitle = editorDialog.playlistName
            root.playlistDescription = editorDialog.playlistDescription
        }
    }

    PlaylistExportDialog {
        id: exportDialog
        bridge: root.bridge
        playlistId: root.playlistId
        playlistName: root.playlistTitle
        objectName: "playlist.detail.exportDialog"
    }
}
