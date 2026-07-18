import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    objectName: "playlistsPage_control"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Playlists"

    property var pl: typeof playlistsBridge !== "undefined" ? playlistsBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string _newName: ""
    property string _addResult: ""
    property string _searchText: ""
    property var _selectedPlaylists: []
    property bool _selectionMode: false
    property bool _confirmBatchDelete: false
    property string _state: "LOADING"
    property string _errorMsg: ""

    PageStateManager {
        id: pageState
        route: "playlists"
        active: true
        onSearchTextChanged: pageState.save()
    }

    Component.onCompleted: {
        if (root.pl && typeof root.pl.refresh !== "undefined")
            root.pl.refresh()
        root._updateState()
    }

    onPlChanged: root._updateState()

    function _updateState() {
        if (!root.pl) { root._state = "ERROR"; return }
        var items = root.pl.playlists
        if (!items || items.length === 0) { root._state = "EMPTY"; return }
        root._state = "READY"
    }

    function toggleSelection(pid) {
        var idx = root._selectedPlaylists.indexOf(pid)
        if (idx >= 0) root._selectedPlaylists.splice(idx, 1)
        else root._selectedPlaylists.push(pid)
    }

    function duplicatePlaylist(pid) {
        if (root.pl && typeof root.pl.duplicatePlaylist !== "undefined")
            root.pl.duplicatePlaylist(pid)
    }

    function shufflePlaylist(pid) {
        if (root.pl && typeof root.pl.playPlaylist !== "undefined")
            root.pl.playPlaylist(pid)
    }

    function deletePlaylist(pid) {
        if (root.pl && typeof root.pl.deletePlaylist !== "undefined")
            root.pl.deletePlaylist(pid)
    }

    function createNewPlaylist(name) {
        if (root.pl && typeof root.pl.createPlaylist !== "undefined")
            root.pl.createPlaylist(name)
    }

    function openEditor() {
        editorDialog.playlistId = -1
        editorDialog.playlistName = ""
        editorDialog.playlistDescription = ""
        editorDialog.open()
    }

    function openImport() {
        importDialog.reset()
        importDialog.open()
    }

    function refresh() {
        if (root.pl && typeof root.pl.refresh !== "undefined")
            root.pl.refresh()
        root._updateState()
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        contentHeight: column.height + MichiTheme.spacing.xl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.md

            HeroMaterial {
                id: playlistHero
                width: parent.width
                height: MichiTheme.typography.heroTitleSize * 5
                radius: MichiTheme.radius.lg
                showGlow: true
                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Playlists"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Gestiona tus listas de reproducción."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            MichiSearchField {
                id: playlistSearch
                width: parent.width * 0.5
                placeholderText: "Buscar playlists..."
                onSearchTextChanged: root._searchText = text
                activeFocusOnTab: true
                KeyNavigation.tab: createPlaylistBtn
                KeyNavigation.backtab: flickable
                Keys.onEscapePressed: { root._searchText = ""; text = "" }
            }

            Row {
                id: actionRow
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    id: createPlaylistBtn
                    objectName: "createPlaylistButton"
                    text: "+ Nueva playlist"
                    variant: "primary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: smartPlaylistBtn
                    KeyNavigation.backtab: playlistSearch
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.openEditor()
                }
                MichiButton {
                    id: smartPlaylistBtn
                    objectName: "smartPlaylistButton"
                    text: "Smart playlist"
                    variant: "secondary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: importPlaylistBtn
                    KeyNavigation.backtab: createPlaylistBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: smartPlaylistDialog.open()
                }
                MichiButton {
                    id: importPlaylistBtn
                    objectName: "importPlaylistButton"
                    text: "Importar"
                    variant: "secondary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: selectPlaylistBtn
                    KeyNavigation.backtab: smartPlaylistBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.openImport()
                }
                MichiButton {
                    id: selectPlaylistBtn
                    objectName: "selectPlaylistButton"
                    text: "Seleccionar"
                    variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: deletePlaylistBtn
                    KeyNavigation.backtab: importPlaylistBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._selectionMode = !root._selectionMode
                    highlighted: root._selectionMode
                }
                MichiButton {
                    id: deletePlaylistBtn
                    objectName: "deletePlaylistButton"
                    text: "Eliminar seleccionadas"
                    variant: "danger"
                    visible: root._selectionMode && root._selectedPlaylists.length > 0
                    activeFocusOnTab: true
                    KeyNavigation.tab: refreshBtn
                    KeyNavigation.backtab: selectPlaylistBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._confirmBatchDelete = true
                }
                MichiButton {
                    id: refreshBtn
                    objectName: "refreshPlaylistsButton"
                    text: "Refrescar"
                    variant: "ghost"
                    visible: root._state !== "LOADING"
                    activeFocusOnTab: true
                    KeyNavigation.backtab: deletePlaylistBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.refresh()
                }
            }

            LoadingState {
                width: parent.width
                visible: root._state === "LOADING"
                title: "Cargando playlists"
                message: "Obteniendo listas de reproducción..."
            }

            EmptyState {
                width: parent.width
                visible: root._state === "EMPTY"
                iconText: ""
                title: "Sin playlists"
                subtitle: "Crea tu primera lista de reproducción para empezar a organizar tu música."
                actionText: "Crear playlist"
                showAction: true
                onActionClicked: root.openEditor()
            }

            ErrorState {
                width: parent.width
                visible: root._state === "ERROR"
                title: "Error al cargar playlists"
                message: !root.pl ? "El servicio de playlists no está disponible."
                                 : "No se pudieron cargar las playlists. Verifica la conexión."
                showRetry: true
                onRetryRequested: root.refresh()
            }

            SectionHeader {
                id: yourPlaylistsHeader
                text: "Tus playlists"
                width: parent.width
                visible: root._state === "READY"
            }

            Flow {
                id: playlistFlow
                width: parent.width
                spacing: MichiTheme.spacing.md
                visible: root._state === "READY"

                Repeater {
                    model: {
                        if (!root.pl || !root.pl.playlists) return []
                        var items = root.pl.playlists
                        if (root._searchText) {
                            var q = root._searchText.toLowerCase()
                            items = items.filter(function(p) {
                                return (p.title || "").toLowerCase().indexOf(q) >= 0
                            })
                        }
                        return items
                    }

                    PlaylistCard {
                        playlistTitle: modelData.title || ""
                        trackCount: modelData.track_count || 0
                        duration: modelData.duration || ""
                        coverKey: modelData.cover_key || ""
                        selected: root._selectedPlaylists.indexOf(modelData.id) >= 0
                        showSelection: root._selectionMode
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()

                        onClicked: {
                            if (root._selectionMode) {
                                root.toggleSelection(modelData.id)
                            } else {
                                if (root.sel && root.sel.hasSelection) {
                                    var result = root.pl.addSelectedTrackToPlaylist(modelData.id)
                                    if (result && result.ok) {
                                        root._addResult = "Canción agregada a \"" + modelData.title + "\""
                                    } else {
                                        root._addResult = result && result.error ? "Error: " + result.error : "Error al agregar"
                                    }
                                } else {
                                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                                        navigationBridge.navigateWithParams("playlist_detail", {
                                            playlistId: modelData.id,
                                            playlistTitle: modelData.title
                                        })
                                }
                            }
                        }

                        onContextMenuRequested: function(action) {
                            if (action === "duplicate") root.duplicatePlaylist(modelData.id)
                            else if (action === "shuffle") root.shufflePlaylist(modelData.id)
                            else if (action === "delete") root.deletePlaylist(modelData.id)
                        }
                    }
                }
            }

            Text {
                text: root._addResult
                color: root._addResult.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.success
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }

        }
    }

    PlaylistEditorDialog {
        id: editorDialog
        bridge: root.pl
        onSaved: function(id, name) {
            if (id < 0 && root.pl && typeof root.pl.createPlaylist !== "undefined")
                root.pl.createPlaylist(name)
            root._addResult = "Creada \"" + name + "\""
            root.refresh()
            forceActiveFocus()
        }
        onCancelled: { forceActiveFocus() }
    }

    PlaylistImportDialog {
        id: importDialog
        bridge: root.pl
        onImportCompleted: function(name, count) {
            root.refresh()
            root._addResult = "Importada \"" + name + "\" (" + count + " canciones)"
            forceActiveFocus()
        }
        onImportCancelled: { forceActiveFocus() }
    }

    SmartPlaylistEditorPage {
        id: smartPlaylistDialog
        bridge: root.pl
        visible: false
        anchors.fill: parent
        onSaved: function(name, rules) {
            root._addResult = "Smart playlist \"" + name + "\" creada"
            root.refresh()
            smartPlaylistDialog.visible = false
            forceActiveFocus()
        }
        onBackRequested: {
            smartPlaylistDialog.visible = false
            forceActiveFocus()
        }
    }

    Dialog {
        id: confirmBatchDelete
        title: "Eliminar playlists"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        visible: root._confirmBatchDelete
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        closePolicy: Popup.CloseOnEscape

        Column {
            spacing: MichiTheme.spacing.md
            Text {
                text: "¿Eliminar " + root._selectedPlaylists.length + " playlist(s) seleccionada(s)?"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            Text {
                text: "Esta acción no se puede deshacer."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }
        }

        onAccepted: {
            for (var i = 0; i < root._selectedPlaylists.length; i++) {
                if (root.pl && typeof root.pl.deletePlaylist !== "undefined")
                    root.pl.deletePlaylist(root._selectedPlaylists[i])
            }
            root._selectedPlaylists = []
            root._selectionMode = false
            root._confirmBatchDelete = false
            root.refresh()
            forceActiveFocus()
        }
        onRejected: { root._confirmBatchDelete = false; forceActiveFocus() }
    }
}
