import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var bridge: null
    property var tracks: []
    property int playlistId: -1
    property bool loading: false
    property string _errorMsg: ""
    property var _selectedTracks: []
    property bool selectionMode: false

    signal playRequested(int index)
    signal removeRequested(int trackId, int index)
    signal moveUpRequested(int index)
    signal moveDownRequested(int index)
    signal selectionChanged()

    function refresh() {
        if (root.bridge && root.playlistId >= 0) {
            var result = root.bridge.getPlaylistDetail(root.playlistId)
            if (result && result.ok) {
                root.tracks = result.tracks || []
                return result
            }
        }
        return null
    }

    function toggleSelection(index) {
        var idx = root._selectedTracks.indexOf(index)
        if (idx >= 0) root._selectedTracks.splice(idx, 1)
        else root._selectedTracks.push(index)
        root.selectionChanged()
    }

    function removeSelected() {
        var indices = root._selectedTracks.slice().sort(function(a, b) { return b - a })
        for (var i = 0; i < indices.length; i++) {
            var idx = indices[i]
            var tid = root.tracks[idx].track_id || 0
            if (tid && root.bridge && typeof root.bridge.removeTrackFromPlaylist !== "undefined") {
                root.bridge.removeTrackFromPlaylist(root.playlistId, tid)
            }
            root.tracks.splice(idx, 1)
        }
        root._selectedTracks = []
        root.selectionMode = false
        root.selectionChanged()
    }

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            visible: root.tracks.length > 0 || root.selectionMode

            Text {
                text: root.tracks.length + " canciones"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            MichiButton {
                text: root.selectionMode ? "Cancelar selección" : "Seleccionar"
                variant: "ghost"
                highlighted: root.selectionMode
                onClicked: {
                    root.selectionMode = !root.selectionMode
                    if (!root.selectionMode) root._selectedTracks = []
                }
                objectName: "playlist.tracklist.selectToggle"
                Accessible.name: root.selectionMode ? "Cancelar selección múltiple" : "Activar selección múltiple"
            }

            MichiButton {
                text: "Quitar seleccionadas"
                variant: "danger"
                visible: root.selectionMode && root._selectedTracks.length > 0
                onClicked: root.removeSelected()
                objectName: "playlist.tracklist.removeSelected"
                Accessible.name: "Quitar canciones seleccionadas"
                Accessible.description: "Quita " + root._selectedTracks.length + " canción(es)"
            }
        }

        ListView {
            id: trackList
            width: parent.width
            height: parent.height - 40
            model: root.tracks
            clip: true
            spacing: 1
            objectName: "playlist.tracklist.list"

            delegate: Rectangle {
                id: delegateRoot
                width: trackList.width
                height: 44
                color: {
                    if (root._selectedTracks.indexOf(index) >= 0) return MichiTheme.colors.accentFaint
                    if (mouseArea.containsMouse) return MichiTheme.colors.surfaceHover
                    return "transparent"
                }
                radius: MichiTheme.radiusSm

                objectName: "playlist.tracklist.item." + index
                Accessible.role: Accessible.ListItem
                Accessible.name: (modelData.title || "") + " por " + (modelData.artist || "")

                Row {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.xs

                    CheckBox {
                        width: 24
                        anchors.verticalCenter: parent.verticalCenter
                        visible: root.selectionMode
                        checked: root._selectedTracks.indexOf(index) >= 0
                        onCheckedChanged: root.toggleSelection(index)
                    }

                    Text {
                        width: 20
                        text: (index + 1) + "."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        visible: !root.selectionMode
                    }

                    Text {
                        width: parent.width * 0.35 - 44
                        text: modelData.title || ""
                        color: modelData.missing ? MichiTheme.colors.textMuted : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.20
                        text: modelData.artist || ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.15
                        text: modelData.album || ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 36
                        text: modelData.duration ? Math.floor(modelData.duration / 60) + ":" + (modelData.duration % 60).toString().padStart(2, "0") : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Item { width: 4; height: 1 }

                    Text {
                        text: "\u25B2"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.captionSize
                        width: 20; height: 20
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        visible: index > 0 && !root.selectionMode
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.moveUpRequested(index)
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: "Mover arriba"
                    }
                    Text {
                        text: "\u25BC"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.captionSize
                        width: 20; height: 20
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        visible: index < root.tracks.length - 1 && !root.selectionMode
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.moveDownRequested(index)
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: "Mover abajo"
                    }

                    Text {
                        text: "\u25B6"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.metaSize
                        width: 20; height: 20
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        visible: !root.selectionMode
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.playRequested(index)
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: "Reproducir"
                    }
                    Text {
                        text: "\u2716"; color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        width: 20; height: 20
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                var tid = modelData.track_id || 0
                                if (tid && root.bridge && typeof root.bridge.removeTrackFromPlaylist !== "undefined") {
                                    var result = root.bridge.removeTrackFromPlaylist(root.playlistId, tid)
                                    if (result && result.ok) {
                                        root.tracks.splice(index, 1)
                                        root.removeRequested(tid, index)
                                    } else {
                                        root._errorMsg = result && result.error ? result.error : "Error al quitar"
                                    }
                                }
                            }
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: "Quitar de la playlist"
                    }
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }

            Text {
                anchors.centerIn: parent
                visible: trackList.count === 0
                text: "Playlist vacía. Agrega canciones desde la biblioteca."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }

        Text {
            text: root._errorMsg
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }
    }
}
