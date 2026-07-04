import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var songs: []
    property var bridge: null

    signal songSelected(string filepath)
    signal songPlayRequested(string filepath)

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            width: parent.width
            height: 32
            color: MichiTheme.colors.surfaceCard

            Row {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                Text { width: parent.width * 0.30; text: "Título"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.25; text: "Artista"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.25; text: "Álbum"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.12; text: "Duración"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
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

                onDoubleClicked: {
                    if (modelData.filepath) {
                        root.songPlayRequested(modelData.filepath)
                        if (root.bridge && typeof root.bridge.play_song !== "undefined") {
                            root.bridge.play_song(modelData.filepath)
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.RightButton
                    onClicked: {
                        contextMenu.x = mouse.x
                        contextMenu.y = mouse.y
                        contextMenu.trackTitle = modelData.title || ""
                        contextMenu.trackArtist = modelData.artist || ""
                        contextMenu.trackFilepath = modelData.filepath || ""
                        contextMenu.visible = true
                    }
                }
            }

            SongContextMenu {
                id: contextMenu
                width: 200
                z: 100
                visible: false

                onPlayClicked: {
                    visible = false
                    if (contextMenu.trackFilepath && root.bridge && typeof root.bridge.play_song !== "undefined") {
                        root.bridge.play_song(contextMenu.trackFilepath)
                    }
                }
                onQueueClicked: { visible = false }
                onAddToPlaylistClicked: {
                    visible = false
                    if (typeof selectionContextBridge !== "undefined" && selectionContextBridge) {
                        selectionContextBridge.setSelected({
                            "id": modelData.id || "",
                            "title": modelData.title || "",
                            "artist": modelData.artist || "",
                            "album": modelData.album || "",
                            "filepath": modelData.filepath || ""
                        })
                    }
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("playlists")
                }
                onEditMetadataClicked: {
                    visible = false
                    if (typeof selectionContextBridge !== "undefined" && selectionContextBridge) {
                        selectionContextBridge.setSelected({
                            "id": modelData.id || "",
                            "title": modelData.title || "",
                            "artist": modelData.artist || "",
                            "album": modelData.album || "",
                            "filepath": modelData.filepath || ""
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
}
