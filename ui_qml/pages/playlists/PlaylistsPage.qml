import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var pl: typeof playlistsBridge !== "undefined" ? playlistsBridge : null
    property var sel: typeof selectionController !== "undefined" ? selectionController : null
    property string _newName: ""
    property string _addResult: ""
    property string _searchText: ""
    property var _selectedPlaylists: []
    property bool _selectionMode: false
    property bool _confirmBatchDelete: false
    property string _state: "LOADING"

    objectName: "playlists.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Playlists"
    Accessible.description: "Gestión de listas de reproducción"

    Component.onCompleted: {
        if (root.pl && typeof root.pl.refresh !== "undefined")
            root.pl.refresh()
        root._state = root.pl && root.pl.playlists && root.pl.playlists.length > 0 ? "READY" : "EMPTY"
    }

    onPlChanged: {
        root._state = root.pl && root.pl.playlists && root.pl.playlists.length > 0 ? "READY" : "EMPTY"
    }

    function toggleSelection(pid) {
        var idx = root._selectedPlaylists.indexOf(pid)
        if (idx >= 0) root._selectedPlaylists.splice(idx, 1)
        else root._selectedPlaylists.push(pid)
        if (root.sel && typeof root.sel.toggle !== "undefined")
            root.sel.toggle(pid)
    }

    function duplicatePlaylist(pid) {
        if (root.pl && typeof root.pl.duplicatePlaylist !== "undefined")
            root.pl.duplicatePlaylist(pid)
    }

    function shufflePlaylist(pid) {
        if (root.pl && typeof root.pl.playPlaylist !== "undefined")
            root.pl.playPlaylist(pid)
    }

    function getFilteredPlaylists() {
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

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "playlists.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (createDialog.opened) createDialog.close()
            if (root._confirmBatchDelete) root._confirmBatchDelete = false
            if (importDialog.opened) importDialog.close()
            if (root._selectionMode) {
                root._selectionMode = false
                root._selectedPlaylists = []
            }
        }

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "playlists.flickableContent"

            Keys.onEscapePressed: {
                if (createDialog.opened) createDialog.close()
                if (root._confirmBatchDelete) root._confirmBatchDelete = false
                if (importDialog.opened) importDialog.close()
            }

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    width: parent.width
                    height: 140
                    radius: MichiTheme.radiusLg
                    showGlow: true
                    objectName: "playlists.hero"

                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xl
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Playlists"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            Accessible.role: Accessible.Heading
                            Accessible.name: "Playlists"
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

                SearchField {
                    id: searchField
                    width: parent.width * 0.5
                    placeholderText: "Buscar playlists..."
                    onSearchTextChanged: root._searchText = text
                    objectName: "playlists.searchField"
                    Accessible.name: "Buscar playlists"
                    KeyNavigation.tab: createBtn
                }

                Row {
                    id: toolbarRow
                    spacing: MichiTheme.spacing.sm
                    objectName: "playlists.toolbarRow"

                    MichiButton {
                        id: createBtn
                        text: "+ Nueva playlist"
                        variant: "primary"
                        onClicked: {
                            editorDialog.playlistId = -1
                            editorDialog.playlistName = ""
                            editorDialog.playlistDescription = ""
                            editorDialog.open()
                        }
                        objectName: "playlists.toolbar.create"
                        Accessible.name: "Crear nueva playlist"
                        KeyNavigation.tab: importBtn
                        KeyNavigation.backtab: searchField
                    }

                    MichiButton {
                        id: importBtn
                        text: "Importar"
                        variant: "secondary"
                        onClicked: importDialog.open()
                        objectName: "playlists.toolbar.import"
                        Accessible.name: "Importar playlist desde archivo"
                        KeyNavigation.tab: smartBtn
                        KeyNavigation.backtab: createBtn
                    }

                    MichiButton {
                        id: smartBtn
                        text: "Smart playlist"
                        variant: "ghost"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("smart_playlist_editor")
                        }
                        objectName: "playlists.toolbar.smart"
                        Accessible.name: "Crear smart playlist"
                        KeyNavigation.tab: selectBtn
                        KeyNavigation.backtab: importBtn
                    }

                    MichiButton {
                        id: selectBtn
                        text: "Seleccionar"
                        variant: "ghost"
                        onClicked: {
                            root._selectionMode = !root._selectionMode
                            if (!root._selectionMode) root._selectedPlaylists = []
                            if (root.sel && typeof root.sel.clear !== "undefined")
                                root.sel.clear()
                        }
                        highlighted: root._selectionMode
                        objectName: "playlists.toolbar.select"
                        Accessible.name: root._selectionMode ? "Desactivar selección múltiple" : "Activar selección múltiple"
                        KeyNavigation.tab: deleteSelectedBtn
                        KeyNavigation.backtab: smartBtn
                    }

                    MichiButton {
                        id: deleteSelectedBtn
                        text: "Eliminar seleccionadas"
                        variant: "danger"
                        visible: root._selectionMode && root._selectedPlaylists.length > 0
                        onClicked: root._confirmBatchDelete = true
                        objectName: "playlists.toolbar.deleteSelected"
                        Accessible.name: "Eliminar playlists seleccionadas"
                        Accessible.description: "Elimina " + root._selectedPlaylists.length + " playlist(s)"
                        KeyNavigation.backtab: selectBtn
                    }
                }

                SectionHeader {
                    id: sectionHeader
                    text: "Tus playlists"
                    width: parent.width
                    objectName: "playlists.section.yourPlaylists"
                    Accessible.name: "Sección de tus playlists"
                }

                LoadingState {
                    width: parent.width
                    height: 200
                    visible: root._state === "LOADING"
                    title: "Cargando playlists"
                    objectName: "playlists.loadingState"
                }

                EmptyState {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: root._state === "EMPTY"
                    title: "Sin playlists"
                    subtitle: "Crea tu primera playlist para empezar a organizar tu música."
                    iconText: "\uD83C\uDFB6"
                    actionText: "Crear playlist"
                    showAction: true
                    objectName: "playlists.emptyState"
                    onActionClicked: {
                        editorDialog.playlistId = -1
                        editorDialog.playlistName = ""
                        editorDialog.playlistDescription = ""
                        editorDialog.open()
                    }
                }

                Flow {
                    id: playlistFlow
                    width: parent.width
                    spacing: MichiTheme.spacing.md
                    visible: root._state === "READY"
                    objectName: "playlists.flow"

                    Repeater {
                        model: root.getFilteredPlaylists()

                        PlaylistCard {
                            playlistTitle: modelData.title || ""
                            trackCount: modelData.track_count || 0
                            duration: modelData.duration || ""
                            coverKey: modelData.cover_key || ""
                            selected: root._selectedPlaylists.indexOf(modelData.id) >= 0
                            showSelection: root._selectionMode
                            objectName: "playlists.card." + index

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
                                            navigationBridge.navigateWithParams("playlist_detail", {playlistId: modelData.id, playlistTitle: modelData.title})
                                    }
                                }
                            }

                            onContextMenuRequested: function(action) {
                                if (action === "duplicate") root.duplicatePlaylist(modelData.id)
                                else if (action === "shuffle") root.shufflePlaylist(modelData.id)
                                else if (action === "delete") {
                                    if (root.pl && typeof root.pl.deletePlaylist !== "undefined")
                                        root.pl.deletePlaylist(modelData.id)
                                } else if (action === "edit") {
                                    editorDialog.playlistId = modelData.id
                                    editorDialog.playlistName = modelData.title
                                    editorDialog.playlistDescription = modelData.description || ""
                                    editorDialog.open()
                                } else if (action === "export") {
                                    exportDirectDialog.playlistId = modelData.id
                                    exportDirectDialog.playlistName = modelData.title
                                    exportDirectDialog.open()
                                }
                            }
                        }
                    }
                }

                Text {
                    id: addResultText
                    text: root._addResult
                    color: root._addResult.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.success
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                    objectName: "playlists.addResult"
                    Accessible.role: Accessible.StatusBar
                    Accessible.name: root._addResult
                }
            }
        }
    }

    PlaylistEditorDialog {
        id: editorDialog
        bridge: root.pl
        objectName: "playlists.editorDialog"
        onSaved: {
            if (root.pl && typeof root.pl.refresh !== "undefined")
                root.pl.refresh()
            root._addResult = "Playlist guardada"
        }
    }

    PlaylistImportDialog {
        id: importDialog
        bridge: root.pl
        objectName: "playlists.importDialog"
        onImportCompleted: {
            if (root.pl && typeof root.pl.refresh !== "undefined")
                root.pl.refresh()
            root._addResult = "Importada \"" + name + "\" (" + count + " canciones)"
            root._state = "READY"
        }
    }

    PlaylistExportDialog {
        id: exportDirectDialog
        bridge: root.pl
        objectName: "playlists.exportDirectDialog"
    }

    Dialog {
        id: confirmBatchDelete
        title: "Eliminar playlists"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        visible: root._confirmBatchDelete
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        objectName: "playlists.confirmBatchDelete"

        Accessible.role: Accessible.Dialog
        Accessible.name: "Confirmar eliminación de playlists"
        Accessible.description: "Confirma la eliminación de las playlists seleccionadas"

        Keys.onEscapePressed: {
            root._confirmBatchDelete = false
            confirmBatchDelete.visible = false
        }

        Text {
            text: "¿Eliminar " + root._selectedPlaylists.length + " playlist(s) seleccionada(s)?"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
        }

        onAccepted: {
            for (var i = 0; i < root._selectedPlaylists.length; i++) {
                if (root.pl && typeof root.pl.deletePlaylist !== "undefined")
                    root.pl.deletePlaylist(root._selectedPlaylists[i])
            }
            root._selectedPlaylists = []
            root._selectionMode = false
            root._confirmBatchDelete = false
            root._state = root.pl && root.pl.playlists && root.pl.playlists.length > 0 ? "READY" : "EMPTY"
        }
        onRejected: root._confirmBatchDelete = false
    }
}
