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

    signal playRequested(int index)
    signal removeRequested(int trackId, int index)
    signal selectionChanged()

    function refresh() {
        if (root.bridge && root.playlistId >= 0) {
            var result = root.bridge.getPlaylistDetail(root.playlistId)
            if (result && result.ok) {
                root.tracks = result.tracks || []
            }
        }
    }

    Column {
        anchors.fill: parent; spacing: MichiTheme.spacing.sm

        Text {
            text: root.tracks.length + " canciones"
            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
            visible: root.tracks.length > 0
        }

        ListView {
            id: trackList; width: parent.width; height: parent.height - 30
            model: root.tracks; clip: true; spacing: 1

            delegate: Rectangle {
                width: trackList.width; height: 40
                color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                radius: MichiTheme.radiusSm

                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                    Text {
                        width: parent.width * 0.40; text: modelData.title || ""
                        color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.25; text: modelData.artist || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.15; text: modelData.album || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 30; text: "▶"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.playRequested(index)
                        }
                    }
                    Text {
                        width: 24; text: "[X]"; color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                        visible: root.bridge !== null
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
                    }
                }

                MouseArea {
                    id: mouseArea; anchors.fill: parent; hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }

            Text {
                anchors.centerIn: parent; visible: trackList.count === 0
                text: "Playlist vacía. Agrega canciones desde la biblioteca."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
            }
        }

        Text {
            text: root._errorMsg; color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.metaSize; visible: text !== ""
        }
    }
}
