import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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
    property string _selFormat: ""

    signal songSelected(string filepath)
    signal songPlayRequested(string filepath)

    Column {
        anchors.fill: parent; spacing: 0

        Rectangle {
            width: parent.width; height: 28; color: MichiTheme.colors.surfaceCard
            Row {
                anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.sm; spacing: 0

                Repeater {
                    model: [
                        {l: "Título", k: "title", w: 0.28},
                        {l: "Artista", k: "artist", w: 0.22},
                        {l: "Álbum", k: "album", w: 0.22},
                        {l: "Dur.", k: "duration", w: 0.08, r: true},
                        {l: "Fmt", k: "format", w: 0.07, r: true},
                    ]
                    Rectangle {
                        width: parent.width * modelData.w; height: parent.height; color: "transparent"
                        Text {
                            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                            horizontalAlignment: modelData.r ? Text.AlignRight : Text.AlignLeft
                            text: modelData.l
                            color: root.bridge && root.bridge.activeSortKey === modelData.k ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: root.bridge && root.bridge.activeSortKey === modelData.k ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightMedium
                        }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { if (root.bridge && typeof root.bridge.sortBy !== "undefined") root.bridge.sortBy(modelData.k) } }
                    }
                }
                Item { width: 28; height: 1 }
            }
        }

        ListView {
            width: parent.width; height: parent.height - 28 - (root.bridge && root.bridge.hasMoreSongs ? 28 : 0)
            model: root.songs; clip: true; boundsBehavior: Flickable.StopAtBounds

            delegate: SongRow {
                width: parent.width
                trackTitle: modelData.title || modelData.filepath || ""
                trackArtist: modelData.artist || ""
                trackAlbum: modelData.album || ""
                trackDuration: modelData.duration ? formatDuration(modelData.duration) : ""
                trackFilepath: modelData.filepath || ""

                onPlayClicked: { if (modelData.filepath) doPlay(modelData.filepath, modelData.title || "") }
                onDoubleClicked: { if (modelData.filepath) doPlay(modelData.filepath, modelData.title || "") }

                onRightClicked: function(mx, my) {
                    root._selId = modelData.id || ""; root._selTitle = modelData.title || ""
                    root._selArtist = modelData.artist || ""; root._selAlbum = modelData.album || ""
                    root._selFilepath = modelData.filepath || ""; root._selFormat = modelData.format || ""
                    if (typeof selectionContextBridge !== "undefined" && selectionContextBridge)
                        selectionContextBridge.setSelected({"id": modelData.id, "title": modelData.title, "artist": modelData.artist, "album": modelData.album, "filepath": modelData.filepath})
                    contextMenu.x = mx + 16; contextMenu.y = my; contextMenu.visible = true
                }
            }

            SongContextMenu {
                id: contextMenu; width: 220; z: 100; visible: false

                onPlayClicked: { visible = false; if (root._selFilepath) doPlay(root._selFilepath, root._selTitle) }
                onQueueClicked: { visible = false
                    if (root.bridge && typeof root.bridge.enqueueSong !== "undefined") {
                        var r = root.bridge.enqueueSong(root._selFilepath)
                        if (root.notif) root.notif.showMessage(r.ok ? "Añadido a la cola" : "Error: " + r.error, r.ok ? "info" : "error")
                    }
                }
                onAddToPlaylistClicked: { visible = false
                    if (typeof selectionContextBridge !== "undefined") selectionContextBridge.setSelected({"id": root._selId, "title": root._selTitle, "artist": root._selArtist, "album": root._selAlbum, "filepath": root._selFilepath})
                    if (typeof navigationBridge !== "undefined") navigationBridge.navigate("playlists")
                }
                onEditMetadataClicked: { visible = false
                    if (typeof selectionContextBridge !== "undefined") selectionContextBridge.setSelected({"id": root._selId, "title": root._selTitle, "artist": root._selArtist, "album": root._selAlbum, "filepath": root._selFilepath})
                    if (typeof navigationBridge !== "undefined") navigationBridge.navigate("metadata_inspector")
                }
                onShowInLibraryClicked: { visible = false
                    if (root.bridge && typeof root.bridge.revealInFileManager !== "undefined") {
                        var r = root.bridge.revealInFileManager(root._selFilepath)
                        if (root.notif) root.notif.showMessage(r.ok ? "Abriendo carpeta..." : "Error: " + r.error, r.ok ? "info" : "error")
                    }
                }
            }
        }

        Row {
            width: parent.width; height: 28; spacing: MichiTheme.spacing.sm
            leftPadding: MichiTheme.spacing.md; visible: root.bridge && root.bridge.hasMoreSongs
            Text { text: "Mostrando " + root.songs.length + " de " + (root.bridge ? root.bridge.visibleCount : 0); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
            MichiButton { text: "Cargar más"; variant: "ghost"; height: 24; onClicked: { if (root.bridge && typeof root.bridge.loadNextPage !== "undefined") root.bridge.loadNextPage() } }
        }

        Item { width: parent.width; height: 180; visible: root.songs.length === 0
            Column { anchors.centerIn: parent; spacing: MichiTheme.spacing.lg
                Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 48; height: 48; radius: 12; color: MichiTheme.colors.accentSurface
                    Text { anchors.centerIn: parent; text: "BL"; color: MichiTheme.colors.accentBlue; font.pixelSize: 18; font.weight: MichiTheme.typography.weightBold; opacity: 0.7 } }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Biblioteca vacía"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Agrega carpetas con música o refresca la biblioteca."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: MichiTheme.spacing.sm
                    MichiButton { text: "Refrescar"; variant: "primary"; onClicked: { if (root.bridge && typeof root.bridge.refresh !== "undefined") root.bridge.refresh() } }
                    MichiButton { text: "Ajustes"; variant: "ghost"; onClicked: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("settings") } }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }

    function doPlay(filepath, title) {
        root.songPlayRequested(filepath)
        if (root.bridge && typeof root.bridge.play_song !== "undefined") {
            var result = root.bridge.play_song(filepath)
            if (root.notif) {
                if (result && result.ok) root.notif.showMessage("Reproduciendo: " + (title || "canción"), "success")
                else root.notif.showMessage("No se pudo reproducir: " + (result && result.error ? result.error : "Error"), "error")
            }
        }
    }
}
