import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var songs: []
    property var bridge: null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _selId: ""
    property string _selTitle: ""
    property string _selArtist: ""
    property string _selAlbum: ""
    property string _selFilepath: ""

    signal songSelected(string filepath)
    signal songPlayRequested(string filepath)

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            width: parent.width; height: 32
            color: MichiTheme.colors.surfaceCard

            Row {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                Text { width: parent.width * 0.30; text: "Título"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.25; text: "Artista"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.25; text: "Álbum"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.08; text: "Dur."; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
                Item { width: 28; height: 1 }
            }
        }

        ListView {
            width: parent.width
            height: parent.height - 32
            model: root.songs
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            delegate: SongRow {
                width: parent.width
                trackTitle: modelData.title || modelData.filepath || ""
                trackArtist: modelData.artist || ""
                trackAlbum: modelData.album || ""
                trackDuration: modelData.duration ? formatDuration(modelData.duration) : ""
                trackFilepath: modelData.filepath || ""

                onPlayClicked: {
                    if (modelData.filepath) {
                        doPlay(modelData.filepath, modelData.title || "", modelData.artist || "", modelData.album || "")
                    }
                }

                onDoubleClicked: {
                    if (modelData.filepath) {
                        doPlay(modelData.filepath, modelData.title || "", modelData.artist || "", modelData.album || "")
                    }
                }

                onRightClicked: {
                    root._selId = modelData.id || ""
                    root._selTitle = modelData.title || ""
                    root._selArtist = modelData.artist || ""
                    root._selAlbum = modelData.album || ""
                    root._selFilepath = modelData.filepath || ""
                    contextMenu.x = mouseX + 16
                    contextMenu.y = mouseY
                    contextMenu.visible = true
                }
            }

            SongContextMenu {
                id: contextMenu
                width: 200; z: 100; visible: false

                onPlayClicked: {
                    visible = false
                    if (root._selFilepath) doPlay(root._selFilepath, root._selTitle, root._selArtist, root._selAlbum)
                }

                onQueueClicked: { visible = false }

                onAddToPlaylistClicked: {
                    visible = false
                    if (typeof selectionContextBridge !== "undefined" && selectionContextBridge) {
                        selectionContextBridge.setSelected({
                            "id": root._selId, "title": root._selTitle,
                            "artist": root._selArtist, "album": root._selAlbum,
                            "filepath": root._selFilepath
                        })
                    }
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("playlists")
                }

                onEditMetadataClicked: {
                    visible = false
                    if (typeof selectionContextBridge !== "undefined" && selectionContextBridge) {
                        selectionContextBridge.setSelected({
                            "id": root._selId, "title": root._selTitle,
                            "artist": root._selArtist, "album": root._selAlbum,
                            "filepath": root._selFilepath
                        })
                    }
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("metadata_inspector")
                }

                onShowInLibraryClicked: { visible = false }
            }

            function formatDuration(secs) {
                var m = Math.floor(secs / 60)
                var s = Math.floor(secs % 60)
                return m + ":" + (s < 10 ? "0" : "") + s
            }
        }
    }

    function doPlay(filepath, title, artist, album) {
        root.songPlayRequested(filepath)
        if (root.bridge && typeof root.bridge.play_song !== "undefined") {
            var result = root.bridge.play_song(filepath)
            if (root.notif) {
                if (result && result.ok) {
                    root.notif.showMessage("Reproduciendo: " + (title || "canción"), "success")
                } else {
                    var err = result && result.error ? result.error : "Error al reproducir"
                    root.notif.showMessage("No se pudo reproducir: " + err, "error")
                }
            }
        }
    }
}
