import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Folder Content View"
    objectName: "folderContentView"
    focus: true
    id: root

    property var bridge: null
    property string currentPath: ""
    property var _tracks: []
    property var _subfolders: []

    signal playFolder(string path)
    signal navigateToFolder(string path)

    function loadFolder(path) {
        if (!path) return
        if (root.bridge && root.bridge.getFolderTracks) {
            root._tracks = root.bridge.getFolderTracks(path) || []
        }
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 28
            color: MichiTheme.colors.surfaceCard
            Text {
                anchors.centerIn: parent
                text: root.currentPath ? "Contenido: " + root.currentPath : "Selecciona una carpeta"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }
        }

        ListView {
            Accessible.role: Accessible.List

            Accessible.name: "ListView"

            activeFocusOnTab: true

            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root._tracks
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: Item {
                width: parent.width; height: 36
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                    anchors.rightMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

                    Text {
                        text: title || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        Layout.fillWidth: true; elide: Text.ElideRight
                    }
                    Text {
                        text: artist || ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        Layout.preferredWidth: 120; elide: Text.ElideRight
                    }
                    Text {
                        text: duration ? formatDuration(duration) : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }

                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: { if (root.bridge && root.bridge.playTrackById) root.bridge.playTrackById(track_id || 0) }
                }
            }

            Item {
                width: parent.width; height: 120
                visible: root._tracks.length === 0 && root.currentPath !== ""
                Text {
                    anchors.centerIn: parent
                    text: "Sin canciones en esta carpeta"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }
        }

        Row {
            Layout.fillWidth: true; Layout.preferredHeight: 32
            leftPadding: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
            visible: root._tracks.length > 0

            MichiButton { text: "Reproducir carpeta"; variant: "primary"; height: 24
                onClicked: { if (root.bridge) root.bridge.playFolder(root.currentPath) }
            }
            MichiButton { text: "Añadir a cola"; variant: "ghost"; height: 24
                onClicked: { if (root.bridge && root.bridge.enqueueSong) {
                    for (var i = 0; i < root._tracks.length; i++) {
                        if (root._tracks[i].filepath) root.bridge.enqueueSong(root._tracks[i].filepath)
                    }
                }}
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
