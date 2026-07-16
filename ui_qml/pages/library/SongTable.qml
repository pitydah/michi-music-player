import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Song Table"
    objectName: "songTable"
    focus: true
    id: root

    property var songs: []
    property var trackModel: null
    property var bridge: null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _selId: ""
    property string _selTitle: ""
    property string _selArtist: ""
    property string _selAlbum: ""
    property string _selFilepath: ""
    property string _selFormat: ""
    property bool _fetchingMore: false

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
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: {
                            if (root.bridge && typeof root.bridge.sortBy !== "undefined") {
                                root.bridge.sortBy(modelData.k)
                            }
                        } }
                    }
                }
                Item { width: 28; height: 1 }
            }
        }

        ListView {
            id: listView
            width: parent.width
            height: parent.height - 28 - (root.trackModel && root.trackModel.hasMore ? 28 : 0) - (root.bridge && root.bridge.hasMoreSongs && !root.trackModel ? 28 : 0)
            model: root.trackModel ? root.trackModel : root.songs
            clip: true; boundsBehavior: Flickable.StopAtBounds

            onContentYChanged: {
                if (!root.trackModel || root._fetchingMore || !root.trackModel.hasMore) return
                if (contentY + height >= contentHeight - 200) {
                    root._fetchingMore = true
                    root.trackModel.fetchMore()
                    root._fetchingMore = false
                }
            }

            delegate: SongRow {
                width: parent.width
                trackTitle: root.trackModel ? (title || "") : (modelData.title || modelData.filepath || "")
                trackArtist: root.trackModel ? (artist || "") : (modelData.artist || "")
                trackAlbum: root.trackModel ? (album || "") : (modelData.album || "")
                trackDuration: root.trackModel ? (duration ? formatDuration(duration) : "") : (modelData.duration ? formatDuration(modelData.duration) : "")
                trackFilepath: ""

                onPlayClicked: {
                    if (root.trackModel) {
                        var tid = trackId || 0
                        if (root.bridge && root.bridge.playTrackById) root.bridge.playTrackById(tid)
                    } else if (modelData.filepath) {
                        doPlay(modelData.filepath, modelData.title || "")
                    }
                }
                onDoubleClicked: {
                    if (root.trackModel) {
                        var tid2 = trackId || 0
                        if (root.bridge && root.bridge.playTrackById) root.bridge.playTrackById(tid2)
                    } else if (modelData.filepath) {
                        doPlay(modelData.filepath, modelData.title || "")
                    }
                }

                onRightClicked: function(mx, my) {
                    var data = root.trackModel ? {id: trackId, title: trackTitle, artist: trackArtist, album: trackAlbum, filepath: ""} : modelData
                    root._selId = data.id || ""; root._selTitle = data.title || ""
                    root._selArtist = data.artist || ""; root._selAlbum = data.album || ""
                    root._selFilepath = data.filepath || ""; root._selFormat = data.format || ""
                    if (typeof selectionContextBridge !== "undefined" && selectionContextBridge)
                        selectionContextBridge.setSelected({"id": data.id, "title": data.title, "artist": data.artist, "album": data.album, "filepath": data.filepath || ""})
                    contextMenu.x = mx + 16; contextMenu.y = my; contextMenu.visible = true
                }
            }

            SongContextMenu {
                id: contextMenu; width: 220; z: 100; visible: false

                onPlayClicked: { visible = false
                    if (root._selFilepath) { doPlay(root._selFilepath, root._selTitle); return }
                    var tid = parseInt(root._selId)
                    if (tid && root.bridge && root.bridge.playTrackById) root.bridge.playTrackById(tid)
                }
                onQueueClicked: { visible = false
                    if (root._selFilepath && root.bridge && root.bridge.enqueueSong) {
                        var r = root.bridge.enqueueSong(root._selFilepath)
                        if (root.notif) root.notif.showMessage(r && r.ok ? "Añadido a la cola" : "Error", r && r.ok ? "info" : "error")
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
                        if (root.notif) root.notif.showMessage(r && r.ok ? "Abriendo carpeta..." : "Error", r && r.ok ? "info" : "error")
                    }
                }
            }
        }

        Row {
            width: parent.width; height: 28; spacing: MichiTheme.spacing.sm
            leftPadding: MichiTheme.spacing.md
            visible: (root.trackModel && root.trackModel.hasMore) || (root.bridge && root.bridge.hasMoreSongs && !root.trackModel)
            Text {
                text: "Mostrando " + (root.trackModel ? root.trackModel.count : root.songs.length) + " de " + (root.trackModel ? root.trackModel.totalCount : (root.bridge ? root.bridge.visibleCount : 0))
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
            }
            MichiButton { text: "Cargar más"; variant: "ghost"; height: 24; onClicked: {
                if (root.trackModel && root.trackModel.hasMore && !root._fetchingMore) {
                    root._fetchingMore = true; root.trackModel.fetchMore(); root._fetchingMore = false
                } else if (root.bridge && typeof root.bridge.loadNextPage !== "undefined") {
                    root.bridge.loadNextPage()
                }
            }}
        }

        Item { width: parent.width; height: 180; visible: (root.trackModel ? root.trackModel.count : root.songs.length) === 0
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
                else root.notif.showMessage("No se pudo reproducir", "error")
            }
        }
    }
}
