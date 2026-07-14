import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var pl: typeof playlistsBridge !== "undefined" ? playlistsBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string _newName: ""
    property string _addResult: ""
    property string _searchText: ""
    property var _selectedPlaylists: []
    property bool _selectionMode: false
    property bool _confirmBatchDelete: false

    Component.onCompleted: {
        if (root.pl && typeof root.pl.refresh !== "undefined")
            root.pl.refresh()
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

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Playlists"; color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Gestiona tus listas de reproducción."; color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            SearchField {
                width: parent.width * 0.5
                placeholderText: "Buscar playlists..."
                onSearchTextChanged: root._searchText = text
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "+ Nueva playlist"; variant: "primary"
                    onClicked: createDialog.open()
                }
                MichiButton { text: "Importar M3U"; variant: "secondary"; onClicked: importDialog.open() }
                MichiButton {
                    text: "Seleccionar"; variant: "ghost"
                    onClicked: root._selectionMode = !root._selectionMode
                    highlighted: root._selectionMode
                }
                MichiButton {
                    text: "Eliminar seleccionadas"; variant: "danger"
                    visible: root._selectionMode && root._selectedPlaylists.length > 0
                    onClicked: root._confirmBatchDelete = true
                }
            }

            SectionHeader { text: "Tus playlists"; width: parent.width }

            Flow {
                width: parent.width; spacing: MichiTheme.spacing.md

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
                                        navigationBridge.navigate("playlist_detail")
                                }
                            }
                        }

                        onContextMenuRequested: function(action) {
                            if (action === "duplicate") root.duplicatePlaylist(modelData.id)
                            else if (action === "shuffle") root.shufflePlaylist(modelData.id)
                            else if (action === "delete") {
                                if (root.pl && typeof root.pl.deletePlaylist !== "undefined")
                                    root.pl.deletePlaylist(modelData.id)
                            }
                        }
                    }
                }
            }

            Text {
                text: root._addResult
                color: root._addResult.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.success
                font.pixelSize: MichiTheme.typography.metaSize; visible: text !== ""
            }

            StatusBadge { text: "Playlists completas — transacciones, importación, exportación"; kind: "info" }
        }
    }

    Dialog {
        id: createDialog
        title: "Nueva playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3

        Column {
            spacing: MichiTheme.spacing.md
            Text { text: "Ingresa el nombre de la playlist:"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            TextField {
                id: nameInput; width: 280
                placeholderText: "Mi nueva playlist"
                onAccepted: createDialog.accept()
            }
        }

        onAccepted: {
            var name = nameInput.text.trim()
            if (name !== "" && root.pl && typeof root.pl.createPlaylist !== "undefined")
                root.pl.createPlaylist(name)
            nameInput.text = ""
        }
        onRejected: { nameInput.text = "" }
    }

    PlaylistImportDialog {
        id: importDialog
        bridge: root.pl
        onImportCompleted: {
            if (root.pl && typeof root.pl.refresh !== "undefined")
                root.pl.refresh()
            root._addResult = "Importada \"" + name + "\" (" + count + " canciones)"
        }
    }

    Dialog {
        id: confirmBatchDelete
        title: "Eliminar playlists"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        visible: root._confirmBatchDelete
        x: (parent.width - width) / 2; y: (parent.height - height) / 3

        Text {
            text: "¿Eliminar " + root._selectedPlaylists.length + " playlist(s) seleccionada(s)?"
            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
        }

        onAccepted: {
            for (var i = 0; i < root._selectedPlaylists.length; i++) {
                if (root.pl && typeof root.pl.deletePlaylist !== "undefined")
                    root.pl.deletePlaylist(root._selectedPlaylists[i])
            }
            root._selectedPlaylists = []
            root._selectionMode = false
            root._confirmBatchDelete = false
        }
        onRejected: root._confirmBatchDelete = false
    }
}
