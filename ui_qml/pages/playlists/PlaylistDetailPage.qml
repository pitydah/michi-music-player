import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    objectName: "playlistDetailPage"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle de playlist"

    property string playlistTitle: ""
    property int playlistId: -1
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

    signal backRequested()

    function loadPlaylist(pid, title) {
        root.playlistId = pid
        root.playlistTitle = title
        root._confirmDelete = false
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

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                MichiButton {
                    Accessible.role: Accessible.Button

                    text: "Volver"
                    variant: "ghost"
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
            }

            EmptyState {
                width: parent.width
                visible: root._state === "EMPTY"
                iconText: "♪"
                title: "Playlist vacía"
                subtitle: "Agrega canciones desde la biblioteca usando el botón 'Agregar canciones'."
                actionText: "Agregar canciones"
                showAction: true
                onActionClicked: root.addTracks()
            }

            ErrorState {
                width: parent.width
                visible: root._state === "ERROR"
                title: "Error al cargar"
                message: root._errorMsg || "No se pudo cargar la playlist."
                showRetry: true
                onRetryRequested: root.refresh()
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root._state === "READY"
                    Accessible.role: Accessible.Button

                MichiButton {
                    id: playAllBtn
                    text: "Reproducir todo"
                    variant: "primary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: shuffleBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.playAll()
                    Accessible.role: Accessible.Button

                }
                MichiButton {
                    id: shuffleBtn
                    text: "Aleatorio"
                    variant: "secondary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: addTracksBtn
                    KeyNavigation.backtab: playAllBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    Accessible.role: Accessible.Button

                    onClicked: root.playShuffled()
                }
                MichiButton {
                    id: addTracksBtn
                    text: "+ Agregar canciones"
                    variant: "secondary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: renameBtn
                    KeyNavigation.backtab: shuffleBtn
                    Keys.onReturnPressed: onClicked()
                    Accessible.role: Accessible.Button

                    Keys.onSpacePressed: onClicked()
                    onClicked: root.addTracks()
                }
                MichiButton {
                    id: renameBtn
                    text: "Renombrar"
                    variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: duplicateBtn
                    KeyNavigation.backtab: addTracksBtn
                    Accessible.role: Accessible.Button

                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: renameDialog.open()
                }
                MichiButton {
                    id: duplicateBtn
                    text: "Duplicar"
                    variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: exportBtn
                    Accessible.role: Accessible.Button

                    KeyNavigation.backtab: renameBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.duplicatePlaylist()
                }
                MichiButton {
                    id: exportBtn
                    text: "Exportar M3U"
                    variant: "ghost"
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button

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
                    Accessible.role: Accessible.Button

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
                    Accessible.role: Accessible.Button

                    visible: root._selectionMode && root._selectedTracks.length > 0
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
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true
                    KeyNavigation.backtab: batchRemoveBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (!root._confirmDelete) root._confirmDelete = true
                        else { root.deletePlaylist(); root._confirmDelete = false }
                    }
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    visible: root._confirmDelete
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._confirmDelete = false
                }
            }

            PlaylistTrackList {
                id: trackListRef
                width: parent.width
                height: Math.min(600, root.tracks.length * 44 + 30)
                bridge: root.bridge
                playlistId: root.playlistId
                tracks: root.tracks
                selectionMode: root._selectionMode
                selectedTracks: root._selectedTracks
                visible: root._state === "READY"
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
        Accessible.role: Accessible.Dialog

        Accessible.name: "Dialog"

                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Item { width: 1; height: MichiTheme.spacing.lg }
        }
    }

    Dialog {
        id: renameDialog
        title: "Renombrar playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

        y: (parent.height - height) / 3
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
                focusPolicy: Qt.StrongFocus
                id: renameInput
                text: root.playlistTitle
                width: parent.width
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
    }

    Keys.onEscapePressed: {
        if (renameDialog.opened) renameDialog.close()
        else if (exportDialog.opened) exportDialog.close()
        else root.backRequested()
    }
}
