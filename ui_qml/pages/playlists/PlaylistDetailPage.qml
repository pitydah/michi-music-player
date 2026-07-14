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
    property var bridge: null
    property var tracks: []
    property bool _confirmDelete: false
    property string _renameText: ""
    property string _errorMsg: ""

    signal backRequested()

    function loadPlaylist(pid, title) {
        playlistId = pid
        playlistTitle = title
        _confirmDelete = false
        trackListRef.playlistId = pid
        trackListRef.bridge = root.bridge
        trackListRef.refresh()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: root.backRequested() }
                Text {
                    text: root.playlistTitle; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Reproducir"; variant: "primary"
                    onClicked: {
                        if (root.bridge && typeof root.bridge.playPlaylist !== "undefined" && root.playlistId >= 0)
                            root.bridge.playPlaylist(root.playlistId)
                    }
                }
                MichiButton {
                    text: "Aleatorio"; variant: "secondary"
                    onClicked: {
                        if (root.bridge && typeof root.bridge.playPlaylist !== "undefined" && root.playlistId >= 0)
                            root.bridge.playPlaylist(root.playlistId)
                    }
                }
                MichiButton {
                    text: "Renombrar"; variant: "secondary"
                    onClicked: { _renameText = root.playlistTitle; renameDialog.open() }
                }
                MichiButton {
                    text: "Duplicar"; variant: "ghost"
                    onClicked: {
                        if (root.bridge && typeof root.bridge.duplicatePlaylist !== "undefined" && root.playlistId >= 0)
                            root.bridge.duplicatePlaylist(root.playlistId)
                    }
                }
                MichiButton {
                    text: "Exportar M3U"; variant: "ghost"
                    onClicked: exportDialog.open()
                }
                MichiButton {
                    text: root._confirmDelete ? "Confirmar" : "Eliminar"
                    variant: root._confirmDelete ? "danger" : "ghost"
                    onClicked: {
                        if (!root._confirmDelete) { root._confirmDelete = true }
                        else {
                            if (root.bridge && typeof root.bridge.deletePlaylist !== "undefined" && root.playlistId >= 0) {
                                root.bridge.deletePlaylist(root.playlistId)
                                root.backRequested()
                            }
                            root._confirmDelete = false
                        }
                    }
                }
                MichiButton {
                    text: "Cancelar"; variant: "ghost"
                    visible: root._confirmDelete
                    onClicked: root._confirmDelete = false
                }
            }

            PlaylistTrackList {
                id: trackListRef
                width: parent.width; height: 400
                bridge: root.bridge
                playlistId: root.playlistId
                tracks: root.tracks
                onPlayRequested: function(index) {
                    if (root.bridge && typeof root.bridge.playPlaylistFromIndex !== "undefined")
                        root.bridge.playPlaylistFromIndex(root.playlistId, index)
                }
                onRemoveRequested: function(trackId, index) {
                    root.tracks.splice(index, 1)
                }
            }

            Text {
                text: root._errorMsg; color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize; visible: text !== ""
            }
        }
    }

    Dialog {
        id: renameDialog
        title: "Renombrar playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3

        Column {
            spacing: MichiTheme.spacing.md
            Text { text: "Nuevo nombre:"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            TextField {
                id: renameInput; text: root._renameText; width: 280
                onAccepted: renameDialog.accept()
            }
        }

        onAccepted: {
            var name = renameInput.text.trim()
            if (name === "") { root._errorMsg = "El nombre no puede estar vacío."; return }
            if (root.bridge && typeof root.bridge.renamePlaylist !== "undefined" && root.playlistId >= 0) {
                var result = root.bridge.renamePlaylist(root.playlistId, name)
                if (result && !result.ok) root._errorMsg = result.error || "Error al renombrar."
                else { root.playlistTitle = name; root._errorMsg = "" }
            }
        }
    }

    PlaylistExportDialog {
        id: exportDialog
        bridge: root.bridge
        playlistId: root.playlistId
        playlistName: root.playlistTitle
    }
}
