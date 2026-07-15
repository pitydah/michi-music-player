import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle de playlist"

    property string playlistTitle: ""
    property int playlistId: -1
    property string playlistDescription: ""
    property string playlistCover: ""
    property int trackCount: 0
    property var bridge: null
    property var tracks: []
    property int trackCount: 0
    property string _duration: ""
    property string _description: ""
    property bool _confirmDelete: false
    property string _errorMsg: ""
    property string _state: "LOADING"
    property var _selectedTracks: []
    property bool _selectionMode: false
    property var _selectedTracks: []
    property bool _selectionMode: false

    signal backRequested()

    function loadPlaylist(pid, title) {
        root.playlistId = pid
        root.playlistTitle = title
        root._confirmDelete = false
        root._selectedTracks = []
        root._selectionMode = false
        root._state = "LOADING"
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
        root._selectedTracks = []
        root._selectionMode = false
        root._state = "LOADING"
        root.refresh()
    }

    function refresh() {
        if (!root.bridge || root.playlistId < 0) return
        var result = root.bridge.getPlaylistDetail(root.playlistId)
        if (result && result.ok) {
            root.tracks = result.tracks || []
            root.trackCount = result.count || root.tracks.length
            root._calcDuration()
            root._state = root.tracks.length > 0 ? "READY" : "EMPTY"
        } else {
            root._state = "ERROR"
            root._errorMsg = result && result.error ? result.error : "Error al cargar playlist"
        }
    }

    function _calcDuration() {
        var total = 0
        for (var i = 0; i < root.tracks.length; i++) {
            var d = root.tracks[i].duration || 0
            if (typeof d === "number") total += d
        }
        var h = Math.floor(total / 3600)
        var m = Math.floor((total % 3600) / 60)
        root._duration = h > 0 ? h + "h " + m + "m" : m + " min"
    }

    function toggleTrackSelection(trackId) {
        var idx = root._selectedTracks.indexOf(trackId)
        if (idx >= 0) root._selectedTracks.splice(idx, 1)
        else root._selectedTracks.push(trackId)
    }

    function removeSelectedTracks() {
        if (!root.bridge || root.playlistId < 0) return
        for (var i = 0; i < root._selectedTracks.length; i++) {
            var tid = root._selectedTracks[i]
            root.bridge.removeTrackFromPlaylist(root.playlistId, tid)
            for (var j = 0; j < root.tracks.length; j++) {
                if (root.tracks[j].track_id === tid) {
                    root.tracks.splice(j, 1)
                    break
                }
            }
        }
        root._selectedTracks = []
        root._selectionMode = false
        root.trackCount = root.tracks.length
        root._calcDuration()
    }

    function moveTrack(fromIndex, toIndex) {
        if (fromIndex < 0 || fromIndex >= root.tracks.length ||
            toIndex < 0 || toIndex >= root.tracks.length || fromIndex === toIndex) return
        if (root.bridge && typeof root.bridge.reorderTrack !== "undefined") {
            var result = root.bridge.reorderTrack(root.playlistId, fromIndex, toIndex)
            if (!result || !result.ok) {
                root._errorMsg = result && result.error ? result.error : "Error al reordenar"
                return
            }
        if (plData) {
            root.playlistDescription = plData.description || ""
            root.playlistCover = plData.cover_key || ""
        }
        var item = root.tracks[fromIndex]
        root.tracks.splice(fromIndex, 1)
        root.tracks.splice(toIndex, 0, item)
    }

    function addTracks() {
        if (typeof actionRegistry !== "undefined" && actionRegistry &&
            typeof actionRegistry.execute !== "undefined")
            actionRegistry.execute("track_add_to_playlist")
    }

    function renamePlaylist(name) {
        if (!root.bridge || typeof root.bridge.renamePlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.renamePlaylist(root.playlistId, name)
        if (result && result.ok) root.playlistTitle = name
        else root._errorMsg = result && result.error ? result.error : "Error al renombrar"
    }

    function duplicatePlaylist() {
        if (!root.bridge || typeof root.bridge.duplicatePlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.duplicatePlaylist(root.playlistId)
        if (!result || !result.ok) root._errorMsg = result && result.error ? result.error : "Error al duplicar"
    }

    function deletePlaylist() {
        if (!root.bridge || typeof root.bridge.deletePlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.deletePlaylist(root.playlistId)
        if (result && result.ok) root.backRequested()
        else root._errorMsg = result && result.error ? result.error : "Error al eliminar"
    }

    function playAll() {
        if (!root.bridge || typeof root.bridge.playPlaylist === "undefined" || root.playlistId < 0) return
        root.bridge.playPlaylist(root.playlistId)
    }

    function playShuffled() {
        if (!root.bridge || typeof root.bridge.playPlaylist === "undefined" || root.playlistId < 0) return
        root.bridge.playPlaylist(root.playlistId)
    }

    function playTrack(index) {
        if (!root.bridge || typeof root.bridge.playPlaylistFromIndex === "undefined" || root.playlistId < 0) return
        root.bridge.playPlaylistFromIndex(root.playlistId, index)
    }

    function removeTrack(trackId, index) {
        if (!root.bridge || typeof root.bridge.removeTrackFromPlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.removeTrackFromPlaylist(root.playlistId, trackId)
        if (result && result.ok) {
            root.tracks.splice(index, 1)
            root.trackCount = root.tracks.length
            root._calcDuration()
        } else {
            root._errorMsg = result && result.error ? result.error : "Error al quitar"
        }
    }

    function exportM3U() {
        exportDialog.open()
    }

    function openTrackAlbum(track) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("album_detail", {trackId: track.track_id})
    }

    function openTrackArtist(track) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("artist_detail", {artist: track.artist})
    }

    Component.onCompleted: {
        if (root.playlistId >= 0) root.refresh()
    Keys.onEscapePressed: {
        if (editorDialog.opened) editorDialog.close()
        else if (exportDialog.opened) exportDialog.close()
        else root.backRequested()
        root._selectedTracks = []
        root._selectionMode = false
        root.trackCount = root.tracks.length
        root._calcDuration()
    }

    function moveTrack(fromIndex, toIndex) {
        if (fromIndex < 0 || fromIndex >= root.tracks.length ||
            toIndex < 0 || toIndex >= root.tracks.length || fromIndex === toIndex) return
        if (root.bridge && typeof root.bridge.reorderTrack !== "undefined") {
            var result = root.bridge.reorderTrack(root.playlistId, fromIndex, toIndex)
            if (!result || !result.ok) {
                root._errorMsg = result && result.error ? result.error : "Error al reordenar"
                return
            }
        }
        var item = root.tracks[fromIndex]
        root.tracks.splice(fromIndex, 1)
        root.tracks.splice(toIndex, 0, item)
    }

    function addTracks() {
        if (typeof actionRegistry !== "undefined" && actionRegistry &&
            typeof actionRegistry.execute !== "undefined")
            actionRegistry.execute("track_add_to_playlist")
    }

    function renamePlaylist(name) {
        if (!root.bridge || typeof root.bridge.renamePlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.renamePlaylist(root.playlistId, name)
        if (result && result.ok) root.playlistTitle = name
        else root._errorMsg = result && result.error ? result.error : "Error al renombrar"
    }

    function duplicatePlaylist() {
        if (!root.bridge || typeof root.bridge.duplicatePlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.duplicatePlaylist(root.playlistId)
        if (!result || !result.ok) root._errorMsg = result && result.error ? result.error : "Error al duplicar"
    }

    function deletePlaylist() {
        if (!root.bridge || typeof root.bridge.deletePlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.deletePlaylist(root.playlistId)
        if (result && result.ok) root.backRequested()
        else root._errorMsg = result && result.error ? result.error : "Error al eliminar"
    }

    function playAll() {
        if (!root.bridge || typeof root.bridge.playPlaylist === "undefined" || root.playlistId < 0) return
        root.bridge.playPlaylist(root.playlistId)
    }

    function playShuffled() {
        if (!root.bridge || typeof root.bridge.playPlaylist === "undefined" || root.playlistId < 0) return
        root.bridge.playPlaylist(root.playlistId)
    }

    function playTrack(index) {
        if (!root.bridge || typeof root.bridge.playPlaylistFromIndex === "undefined" || root.playlistId < 0) return
        root.bridge.playPlaylistFromIndex(root.playlistId, index)
    }

    function removeTrack(trackId, index) {
        if (!root.bridge || typeof root.bridge.removeTrackFromPlaylist === "undefined" || root.playlistId < 0) return
        var result = root.bridge.removeTrackFromPlaylist(root.playlistId, trackId)
        if (result && result.ok) {
            root.tracks.splice(index, 1)
            root.trackCount = root.tracks.length
            root._calcDuration()
        } else {
            root._errorMsg = result && result.error ? result.error : "Error al quitar"
        }
    }

    function exportM3U() {
        exportDialog.open()
    }

    function openTrackAlbum(track) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("album_detail", {trackId: track.track_id})
    }

    function openTrackArtist(track) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("artist_detail", {artist: track.artist})
    }

    Component.onCompleted: {
        if (root.playlistId >= 0) root.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        objectName: "playlistDetailFlickable"
        Accessible.name: "Detalle de playlist"
        focus: true
        objectName: "playlist.detail.flickable"
        activeFocusOnTab: true
        objectName: "playlistDetailFlickable"
        Accessible.name: "Detalle de playlist"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                objectName: "playlist.detail.header"

                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "playlistDetailBackButton"
                    Accessible.name: "Volver a playlists"
                    activeFocusOnTab: true
                    KeyNavigation.tab: playAllBtn
                    KeyNavigation.backtab: flickable
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.backRequested()
                }

                Item { Layout.fillWidth: true; height: 1; width: 1 }

                width: parent.width

                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "playlistDetailBackButton"
                    Accessible.name: "Volver a playlists"
                    activeFocusOnTab: true
                    KeyNavigation.tab: playAllBtn
                    KeyNavigation.backtab: flickable
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.backRequested()
                }

                Item { Layout.fillWidth: true; height: 1; width: 1 }

                Text {
                    text: root.playlistTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    Accessible.role: Accessible.Heading
                    Accessible.name: root.playlistTitle
                }

                Item { Layout.fillWidth: true; height: 1; width: 1 }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Row {
                spacing: MichiTheme.spacing.lg
                width: parent.width

                Column {
                    spacing: MichiTheme.spacing.xs
                    Text {
                        text: root.trackCount + " canciones"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        Accessible.name: root.trackCount + " canciones"
                    }
                    Text {
                        text: root._duration.length > 0 ? "Duración: " + root._duration : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                    Text {
                        text: root._description
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: 400
                        visible: root._description !== ""
                    }
                }
            }

            Text {
                text: root.playlistDescription
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.playlistDescription !== ""
                wrapMode: Text.WordWrap
                width: parent.width * 0.6
                    Accessible.name: root.playlistTitle
                }

                Item { Layout.fillWidth: true; height: 1; width: 1 }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Row {
                spacing: MichiTheme.spacing.lg
                width: parent.width

                Column {
                    spacing: MichiTheme.spacing.xs
                    Text {
                        text: root.trackCount + " canciones"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        Accessible.name: root.trackCount + " canciones"
                    }
                    Text {
                        text: root._duration.length > 0 ? "Duración: " + root._duration : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                    Text {
                        text: root._description
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: 400
                        visible: root._description !== ""
                    }
                }
            }

            LoadingState {
                width: parent.width
                visible: root._state === "LOADING"
                title: "Cargando playlist"
                message: "Obteniendo canciones..."
                objectName: "playlistDetailLoadingState"
                Accessible.name: "Cargando playlist"
            }

            EmptyState {
                width: parent.width
                visible: root._state === "EMPTY"
                iconText: "♪"
                title: "Playlist vacía"
                subtitle: "Agrega canciones desde la biblioteca usando el botón 'Agregar canciones'."
                actionText: "Agregar canciones"
                showAction: true
                objectName: "playlistDetailEmptyState"
                Accessible.name: "Playlist vacía"
                onActionClicked: root.addTracks()
            }

            ErrorState {
                width: parent.width
                visible: root._state === "ERROR"
                title: "Error al cargar"
                message: root._errorMsg || "No se pudo cargar la playlist."
                showRetry: true
                objectName: "playlistDetailErrorState"
                Accessible.name: "Error al cargar playlist"
                onRetryRequested: root.refresh()
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root._state === "READY"
                objectName: "playlist.detail.toolbar"

                MichiButton {
                    id: playAllBtn
                    text: "Reproducir todo"
                    variant: "primary"
                    objectName: "playAllButton"
                    Accessible.name: "Reproducir todo"
                    activeFocusOnTab: true
                    KeyNavigation.tab: shuffleBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.playAll()
                }
                MichiButton {
                    id: shuffleBtn
                    text: "Aleatorio"
                    variant: "secondary"
                    objectName: "shuffleButton"
                    Accessible.name: "Reproducir aleatorio"
                    activeFocusOnTab: true
                    KeyNavigation.tab: addTracksBtn
                    KeyNavigation.backtab: playAllBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.playShuffled()
                }
                MichiButton {
                    id: addTracksBtn
                    text: "+ Agregar canciones"
                    variant: "secondary"
                    objectName: "addTracksButton"
                    Accessible.name: "Agregar canciones"
                    activeFocusOnTab: true
                    KeyNavigation.tab: renameBtn
                    KeyNavigation.backtab: shuffleBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.addTracks()
                }
                MichiButton {
                    id: renameBtn
                    text: "Renombrar"
                    variant: "ghost"
                    objectName: "renamePlaylistButton"
                    Accessible.name: "Renombrar playlist"
                    activeFocusOnTab: true
                    KeyNavigation.tab: duplicateBtn
                    KeyNavigation.backtab: addTracksBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: renameDialog.open()
                }
                MichiButton {
                    id: duplicateBtn
                    text: "Duplicar"
                    variant: "ghost"
                    objectName: "duplicatePlaylistButton"
                    Accessible.name: "Duplicar playlist"
                    activeFocusOnTab: true
                    KeyNavigation.tab: exportBtn
                    KeyNavigation.backtab: renameBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.duplicatePlaylist()
                }
                MichiButton {
                    id: exportBtn
                    text: "Exportar M3U"
                    variant: "ghost"
                    objectName: "exportM3UButton"
                    Accessible.name: "Exportar playlist como M3U"
                    activeFocusOnTab: true
                    KeyNavigation.tab: selectToggleBtn
                    KeyNavigation.backtab: duplicateBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.exportM3U()
                }
                MichiButton {
                    id: selectToggleBtn
                    text: root._selectionMode ? "Cancelar selección" : "Seleccionar"
                    variant: "ghost"
                    highlighted: root._selectionMode
                    objectName: "selectToggleButton"
                    Accessible.name: root._selectionMode ? "Cancelar selección" : "Seleccionar canciones"
                    activeFocusOnTab: true
                    KeyNavigation.tab: batchRemoveBtn
                    KeyNavigation.backtab: exportBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._selectionMode = !root._selectionMode
                }
                MichiButton {
                    id: batchRemoveBtn
                    text: "Quitar seleccionadas (" + root._selectedTracks.length + ")"
                    variant: "danger"
                    visible: root._selectionMode && root._selectedTracks.length > 0
                    objectName: "batchRemoveButton"
                    Accessible.name: "Quitar canciones seleccionadas"
                    activeFocusOnTab: true
                    KeyNavigation.tab: deleteBtn
                    KeyNavigation.backtab: selectToggleBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.removeSelectedTracks()
                }
                MichiButton {
                    id: deleteBtn
                    text: root._confirmDelete ? "Confirmar eliminar" : "Eliminar playlist"
                    text: root._confirmDelete ? "Confirmar" : "Eliminar"
                visible: root._state === "READY"
                MichiButton {
                    id: playAllBtn
                    text: "Reproducir todo"
                    variant: "primary"
                    objectName: "playAllButton"
                    Accessible.name: "Reproducir todo"
                    activeFocusOnTab: true
                    KeyNavigation.tab: shuffleBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.playAll()
                }
                MichiButton {
                    id: shuffleBtn
                    text: "Aleatorio"
                    variant: "secondary"
                    objectName: "shuffleButton"
                    Accessible.name: "Reproducir aleatorio"
                    activeFocusOnTab: true
                    KeyNavigation.tab: addTracksBtn
                    KeyNavigation.backtab: playAllBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.playShuffled()
                }
                MichiButton {
                    id: addTracksBtn
                    text: "+ Agregar canciones"
                    variant: "secondary"
                    objectName: "addTracksButton"
                    Accessible.name: "Agregar canciones"
                    activeFocusOnTab: true
                    KeyNavigation.tab: renameBtn
                    KeyNavigation.backtab: shuffleBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.addTracks()
                }
                MichiButton {
                    id: renameBtn
                    text: "Renombrar"
                    variant: "ghost"
                    objectName: "renamePlaylistButton"
                    Accessible.name: "Renombrar playlist"
                    activeFocusOnTab: true
                    KeyNavigation.tab: duplicateBtn
                    KeyNavigation.backtab: addTracksBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: renameDialog.open()
                }
                MichiButton {
                    id: duplicateBtn
                    text: "Duplicar"
                    variant: "ghost"
                    objectName: "duplicatePlaylistButton"
                    Accessible.name: "Duplicar playlist"
                    activeFocusOnTab: true
                    KeyNavigation.tab: exportBtn
                    KeyNavigation.backtab: renameBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.duplicatePlaylist()
                }
                MichiButton {
                    id: exportBtn
                    text: "Exportar M3U"
                    variant: "ghost"
                    objectName: "exportM3UButton"
                    Accessible.name: "Exportar playlist como M3U"
                    activeFocusOnTab: true
                    KeyNavigation.tab: selectToggleBtn
                    KeyNavigation.backtab: duplicateBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.exportM3U()
                }
                MichiButton {
                    id: selectToggleBtn
                    text: root._selectionMode ? "Cancelar selección" : "Seleccionar"
                    variant: "ghost"
                    highlighted: root._selectionMode
                    objectName: "selectToggleButton"
                    Accessible.name: root._selectionMode ? "Cancelar selección" : "Seleccionar canciones"
                    activeFocusOnTab: true
                    KeyNavigation.tab: batchRemoveBtn
                    KeyNavigation.backtab: exportBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._selectionMode = !root._selectionMode
                }
                MichiButton {
                    id: batchRemoveBtn
                    text: "Quitar seleccionadas (" + root._selectedTracks.length + ")"
                    variant: "danger"
                    visible: root._selectionMode && root._selectedTracks.length > 0
                    objectName: "batchRemoveButton"
                    Accessible.name: "Quitar canciones seleccionadas"
                    activeFocusOnTab: true
                    KeyNavigation.tab: deleteBtn
                    KeyNavigation.backtab: selectToggleBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.removeSelectedTracks()
                }
                MichiButton {
                    id: deleteBtn
                    text: root._confirmDelete ? "Confirmar eliminar" : "Eliminar playlist"
                    variant: root._confirmDelete ? "danger" : "ghost"
                    objectName: "deletePlaylistButton"
                    Accessible.name: root._confirmDelete ? "Confirmar eliminar playlist" : "Eliminar playlist"
                    activeFocusOnTab: true
                    KeyNavigation.backtab: batchRemoveBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (!root._confirmDelete) root._confirmDelete = true
                        else { root.deletePlaylist(); root._confirmDelete = false }
                        if (!root._confirmDelete) { root._confirmDelete = true }
                        else { root.deletePlaylist() }
                        if (!root._confirmDelete) root._confirmDelete = true
                        else { root.deletePlaylist(); root._confirmDelete = false }
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
                    objectName: "cancelDeleteButton"
                    Accessible.name: "Cancelar eliminación"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
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
                height: Math.min(600, root.tracks.length * 44 + 30)
                bridge: root.bridge
                playlistId: root.playlistId
                tracks: root.tracks
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
                height: Math.min(600, root.tracks.length * 44 + 30)
                bridge: root.bridge
                playlistId: root.playlistId
                tracks: root.tracks
                selectionMode: root._selectionMode
                selectedTracks: root._selectedTracks
                visible: root._state === "READY"
                objectName: "playlistTrackList"
                Accessible.name: "Lista de canciones"
                onPlayRequested: function(index) { root.playTrack(index) }
                onRemoveRequested: function(trackId, index) { root.removeTrack(trackId, index) }
                onMoveUpRequested: function(index) { root.moveTrack(index, index - 1) }
                onMoveDownRequested: function(index) { root.moveTrack(index, index + 1) }
                onToggleSelection: function(trackId) { root.toggleTrackSelection(trackId) }
                onOpenAlbumRequested: function(track) { root.openTrackAlbum(track) }
                onOpenArtistRequested: function(track) { root.openTrackArtist(track) }
            }

            Text {
                text: root._errorMsg
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
                wrapMode: Text.WordWrap
                width: parent.width
                Accessible.name: root._errorMsg
                Accessible.name: root._errorMsg
            }

            Item { width: 1; height: MichiTheme.spacing.lg }
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
    Dialog {
        id: renameDialog
        title: "Renombrar playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        objectName: "renamePlaylistDialog"
        Accessible.role: Accessible.Dialog
        Accessible.name: "Renombrar playlist"
        closePolicy: Popup.CloseOnEscape

        Column {
            spacing: MichiTheme.spacing.md
            width: 300

            Text {
                text: "Nuevo nombre:"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextField {
                id: renameInput
                text: root.playlistTitle
                width: parent.width
                objectName: "renamePlaylistInput"
                Accessible.name: "Nuevo nombre"
                activeFocusOnTab: true
                Keys.onReturnPressed: renameDialog.accept()
                Keys.onEscapePressed: renameDialog.reject()
            }
        }

        onAccepted: {
            var name = renameInput.text.trim()
            if (name === "") { root._errorMsg = "El nombre no puede estar vacío."; return }
            root.renamePlaylist(name)
            root._errorMsg = ""
        }
        onRejected: { forceActiveFocus() }
        onOpened: { renameInput.selectAll(); renameInput.forceActiveFocus() }
    }

    PlaylistExportDialog {
        id: exportDialog
        bridge: root.bridge
        playlistId: root.playlistId
        playlistName: root.playlistTitle
        objectName: "playlist.detail.exportDialog"
        objectName: "playlist.detail.exportDialog"
        objectName: "playlistExportDialog"
        Accessible.name: "Exportar playlist"
    }

    Keys.onEscapePressed: {
        if (renameDialog.opened) renameDialog.close()
        else if (exportDialog.opened) exportDialog.close()
        else root.backRequested()
    }
}
