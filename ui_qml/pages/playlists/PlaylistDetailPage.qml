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
        if (root.bridge && typeof root.bridge.getPlaylistDetail !== "undefined") {
            var result = root.bridge.getPlaylistDetail(pid)
            if (result && result.ok) {
                tracks = result.tracks || []
            }
        }
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
                    text: "Renombrar"; variant: "secondary"
                    onClicked: {
                        _renameText = root.playlistTitle
                        renameDialog.open()
                    }
                }
                MichiButton {
                    text: root._confirmDelete ? "Confirmar eliminación" : "Eliminar"
                    variant: root._confirmDelete ? "danger" : "ghost"
                    onClicked: {
                        if (!root._confirmDelete) {
                            root._confirmDelete = true
                        } else {
                            if (root.bridge && typeof root.bridge.deletePlaylist !== "undefined" && root.playlistId >= 0) {
                                root.bridge.deletePlaylist(root.playlistId)
                                root.backRequested()
                            }
                            root._confirmDelete = false
                        }
                    }
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    visible: root._confirmDelete
                    onClicked: root._confirmDelete = false
                }
            }

            Text {
                text: tracks.length > 0 ? tracks.length + " canciones" : "Contenido de la playlist"
                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
            }

            Repeater {
                model: root.tracks

                Rectangle {
                    width: parent.width; height: 32; color: "transparent"
                    Row {
                        anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                        Text {
                            width: parent.width * 0.45; text: modelData.title || ""
                            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.30; text: modelData.artist || ""
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                    Text {
                        width: parent.width * 0.10; text: modelData.album || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 24; text: "[X]"; color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        visible: root.bridge && typeof root.bridge.removeTrackFromPlaylist !== "undefined"

                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.bridge && typeof root.bridge.removeTrackFromPlaylist !== "undefined") {
                                    var result = root.bridge.removeTrackFromPlaylist(root.playlistId, modelData.track_id)
                                    if (result && result.ok) {
                                        root._errorMsg = ""
                                        root.loadPlaylist(root.playlistId, root.playlistTitle)
                                    } else {
                                        root._errorMsg = result && result.error ? result.error : "Error al quitar canción"
                                    }
                                }
                            }
                        }
                    }
                }
            }
            }

            Text {
                text: root.tracks.length === 0 ? "Esta playlist está vacía. Agrega canciones desde la biblioteca." : ""
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }

            Text {
                text: root._errorMsg
                color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }
        }
    }

    Dialog {
        id: renameDialog
        title: "Renombrar playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3

        Column {
            spacing: MichiTheme.spacing.md
            Text { text: "Nuevo nombre:"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            TextField {
                id: renameInput
                text: root._renameText
                width: 280
                onAccepted: renameDialog.accept()
            }
        }

        onAccepted: {
            var name = renameInput.text.trim()
            if (name === "") {
                root._errorMsg = "El nombre no puede estar vacío."
                return
            }
            if (root.bridge && typeof root.bridge.renamePlaylist !== "undefined" && root.playlistId >= 0) {
                var result = root.bridge.renamePlaylist(root.playlistId, name)
                if (result && !result.ok) {
                    root._errorMsg = result.error || "Error al renombrar."
                } else {
                    root.playlistTitle = name
                    root._errorMsg = ""
                }
            }
        }
    }
}
