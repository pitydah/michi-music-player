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
    property bool selectionMode: false
    property var selectedTracks: []
    property string _errorMsg: ""
    property var _selectedTracks: []
    property bool selectionMode: false

    signal playRequested(int index)
    signal removeRequested(int trackId, int index)
    signal moveUpRequested(int index)
    signal moveDownRequested(int index)
    signal toggleSelection(int trackId)
    signal openAlbumRequested(var track)
    signal openArtistRequested(var track)
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
            spacing: MichiTheme.spacing.sm
            visible: root.tracks.length > 0

            Text {
                text: root.tracks.length + " canciones"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: root._getMissingCount() > 0 ? "(" + root._getMissingCount() + " faltantes)" : ""
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root._getMissingCount() > 0
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        function _getMissingCount() {
            var count = 0
            for (var i = 0; i < root.tracks.length; i++) {
                if (root.tracks[i].missing) count++
            }
            return count
        }

        ListView {
            id: trackList
            width: parent.width
            height: parent.height - 30
            model: root.tracks
            clip: true
            spacing: 1
            objectName: "playlistTrackListView"
            Accessible.role: Accessible.List
            Accessible.name: "Lista de canciones"
            keyNavigationWraps: true

            delegate: Rectangle {
                width: trackList.width
                height: 44
                color: root.selectedTracks.indexOf(modelData.track_id || 0) >= 0
                       ? MichiTheme.colors.accentFaint
                       : mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                radius: MichiTheme.radiusSm

                objectName: "playlist.tracklist.item." + index
                Accessible.role: Accessible.ListItem
                Accessible.name: (modelData.title || "") + " por " + (modelData.artist || "")

                Row {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    CheckBox {
                        width: 24
                        anchors.verticalCenter: parent.verticalCenter
                        visible: root.selectionMode
                        checked: root.selectedTracks.indexOf(modelData.track_id || 0) >= 0
                        objectName: "trackCheckbox_" + index
                        Accessible.name: "Seleccionar " + (modelData.title || "")
                        onCheckedChanged: root.toggleSelection(modelData.track_id || 0)
                    }

                    Text {
                        width: parent.width * 0.30
                        text: (index + 1) + ". " + (modelData.title || "")
                        color: modelData.missing ? MichiTheme.colors.textMuted : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: modelData.missing ? MichiTheme.typography.weightNormal : MichiTheme.typography.weightMedium
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
                        width: 40
                        text: modelData.missing ? "FALTANTE" : ""
                        color: MichiTheme.colors.warning
                        font.pixelSize: MichiTheme.typography.badgeSize
                        font.weight: MichiTheme.typography.weightBold
                        anchors.verticalCenter: parent.verticalCenter
                        visible: modelData.missing
                    }
                    Text {
                        width: 24
                        text: "▶"
                        color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.bodySize
                        anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.playRequested(index)
                        }
                        visible: !modelData.missing
                    }
                    Text {
                        width: 16
                        text: "↑"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        visible: index > 0
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.moveUpRequested(index)
                        }
                    }
                    Text {
                        width: 16
                        text: "↓"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        visible: index < root.tracks.length - 1
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.moveDownRequested(index)
                        }
                    }
                    Text {
                        width: 24
                        text: "[X]"
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                var tid = modelData.track_id || 0
                                if (tid) root.removeRequested(tid, index)
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
                    acceptedButtons: Qt.RightButton
                    onClicked: contextMenu.popup()
                }

                Menu {
                    id: contextMenu
                    objectName: "trackContextMenu_" + index
                    Accessible.name: "Menú contextual"

                    MenuItem {
                        text: "Reproducir"
                        objectName: "trackPlayMenuItem_" + index
                        Accessible.name: "Reproducir"
                        enabled: !modelData.missing
                        onTriggered: root.playRequested(index)
                    }
                    MenuItem {
                        text: "Ir al álbum"
                        objectName: "trackOpenAlbumMenuItem_" + index
                        Accessible.name: "Ir al álbum"
                        onTriggered: root.openAlbumRequested(modelData)
                    }
                    MenuItem {
                        text: "Ir al artista"
                        objectName: "trackOpenArtistMenuItem_" + index
                        Accessible.name: "Ir al artista"
                        onTriggered: root.openArtistRequested(modelData)
                    }
                    MenuSeparator {}
                    MenuItem {
                        text: "Subir"
                        objectName: "trackMoveUpMenuItem_" + index
                        Accessible.name: "Subir"
                        enabled: index > 0
                        onTriggered: root.moveUpRequested(index)
                    }
                    MenuItem {
                        text: "Bajar"
                        objectName: "trackMoveDownMenuItem_" + index
                        Accessible.name: "Bajar"
                        enabled: index < root.tracks.length - 1
                        onTriggered: root.moveDownRequested(index)
                    }
                    MenuSeparator {}
                    MenuItem {
                        text: "Quitar de playlist"
                        objectName: "trackRemoveMenuItem_" + index
                        Accessible.name: "Quitar de playlist"
                        onTriggered: {
                            var tid = modelData.track_id || 0
                            if (tid) root.removeRequested(tid, index)
                        }
                    }
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
