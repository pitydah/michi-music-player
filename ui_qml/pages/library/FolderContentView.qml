import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "folderContentView"
    focus: true

    property var bridge: null
    property string currentPath: ""
    property var _tracks: []
    property string searchText: ""
    property bool loading: false
    readonly property var visibleTracks: root.filterTracks(root._tracks, root.searchText)
    readonly property int visibleTrackCount: root.visibleTracks.length

    signal playFolder(string path)
    signal navigateToFolder(string path)

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Contenido de carpeta")
    Accessible.description: root.currentPath || qsTr("Selecciona una carpeta")

    function loadFolder(path) {
        root.currentPath = path || ""
        if (!root.currentPath) {
            root._tracks = []
            return
        }
        root.loading = true
        try {
            if (root.bridge && root.bridge.getFolderTracks)
                root._tracks = root.bridge.getFolderTracks(root.currentPath) || []
            else
                root._tracks = []
        } finally {
            root.loading = false
        }
        if (trackList.currentIndex >= root._tracks.length)
            trackList.currentIndex = root._tracks.length > 0 ? 0 : -1
    }

    function filterTracks(tracks, query) {
        var normalized = (query || "").trim().toLocaleLowerCase()
        if (normalized === "")
            return tracks || []
        return (tracks || []).filter(function(track) {
            var haystack = [
                track.title || "",
                track.artist || "",
                track.album || "",
                track.genre || "",
                track.format || ""
            ].join(" ").toLocaleLowerCase()
            return haystack.indexOf(normalized) >= 0
        })
    }

    function trackIdOf(track) {
        return track ? (track.track_id || track.trackId || track.id || 0) : 0
    }

    function playTrack(track) {
        var trackId = root.trackIdOf(track)
        if (trackId && root.bridge && root.bridge.playTrackById)
            root.bridge.playTrackById(trackId)
    }

    function playSelected() {
        if (trackList.currentIndex < 0 ||
                trackList.currentIndex >= root.visibleTracks.length)
            return
        root.playTrack(root.visibleTracks[trackList.currentIndex])
    }

    function playCurrentFolder() {
        if (!root.currentPath)
            return
        if (root.bridge && root.bridge.playFolder)
            root.bridge.playFolder(root.currentPath)
        else
            root.playFolder(root.currentPath)
    }

    function enqueueFolder() {
        if (!root.bridge || !root.bridge.enqueueSong)
            return
        for (var index = 0; index < root._tracks.length; index++) {
            var filepath = root._tracks[index].filepath || ""
            if (filepath)
                root.bridge.enqueueSong(filepath)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.surfaceCard
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard
            clip: true

            ListView {
                id: trackList
                objectName: "folderTrackList"
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xs
                model: root.visibleTracks
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                spacing: 2
                activeFocusOnTab: true
                focus: true
                keyNavigationWraps: false
                cacheBuffer: 260

                Keys.onReturnPressed: root.playSelected()
                Keys.onEnterPressed: root.playSelected()
                Keys.onSpacePressed: root.playSelected()

                onCurrentIndexChanged: {
                    if (currentIndex >= 0)
                        positionViewAtIndex(currentIndex, ListView.Contain)
                }

                ScrollBar.vertical: ScrollBar {
                    width: 8
                    policy: ScrollBar.AsNeeded
                }

                delegate: Rectangle {
                    id: trackRow
                    required property int index
                    required property var modelData

                    width: trackList.width
                    height: 48
                    radius: MichiTheme.radius.md
                    readonly property bool selected: ListView.isCurrentItem
                    readonly property var track: trackRow.modelData || ({})
                    color: selected
                           ? MichiTheme.colors.accentSelection
                           : rowMouse.containsMouse
                             ? MichiTheme.colors.surfaceHover
                             : "transparent"
                    border.width: selected ? MichiTheme.borderWidth : 0
                    border.color: MichiTheme.colors.borderActive

                    Accessible.role: Accessible.Button
                    Accessible.name: track.title || qsTr("Canción sin título")
                    Accessible.description: (track.artist || qsTr("Artista desconocido")) +
                                            ", " + root.formatDuration(track.duration || 0)
                    Accessible.onPressAction: root.playTrack(track)

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        acceptedButtons: Qt.LeftButton
                        onPressed: trackList.currentIndex = trackRow.index
                        onDoubleClicked: root.playTrack(trackRow.track)
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.md

                        Text {
                            Layout.preferredWidth: 28
                            text: track.track_number || track.trackNumber || trackRow.index + 1
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            horizontalAlignment: Text.AlignRight
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Text {
                                Layout.fillWidth: true
                                text: track.title || qsTr("Canción sin título")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: trackRow.selected
                                             ? MichiTheme.typography.weightSemiBold
                                             : MichiTheme.typography.weightMedium
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: track.artist || qsTr("Artista desconocido")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            text: root.formatDuration(track.duration || 0)
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }

                        Rectangle {
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 32
                            radius: 16
                            color: playMouse.pressed
                                   ? MichiTheme.colors.accentSecondary
                                   : rowMouse.containsMouse || trackRow.selected
                                     ? MichiTheme.colors.accentPrimary
                                     : MichiTheme.colors.surfaceElevation3

                            Accessible.role: Accessible.Button
                            Accessible.name: qsTr("Reproducir %1").arg(
                                                 track.title || qsTr("canción")
                                             )
                            Accessible.onPressAction: root.playTrack(trackRow.track)

                            MichiIcon {
                                anchors.centerIn: parent
                                source: "../../../icons/sidebar/play.svg"
                                size: 14
                                color: rowMouse.containsMouse || trackRow.selected
                                       ? MichiTheme.colors.textOnAccent
                                       : MichiTheme.colors.textSecondary
                                accessibleName: ""
                                Accessible.ignored: true
                            }

                            MouseArea {
                                id: playMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    trackList.currentIndex = trackRow.index
                                    root.playTrack(trackRow.track)
                                }
                            }
                        }
                    }
                }
            }

            Column {
                anchors.centerIn: parent
                spacing: MichiTheme.spacing.sm
                visible: !root.loading && root.visibleTracks.length === 0

                MichiIcon {
                    anchors.horizontalCenter: parent.horizontalCenter
                    iconKey: root.currentPath ? "songs" : "folders"
                    size: MichiTheme.iconSizeLarge
                    color: MichiTheme.colors.textMuted
                    accessibleName: ""
                    Accessible.ignored: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.searchText !== ""
                          ? qsTr("Sin coincidencias en esta carpeta")
                          : root.currentPath
                            ? qsTr("Sin canciones en esta carpeta")
                            : qsTr("Selecciona una carpeta")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
            }
        }
    }

    function formatDuration(seconds) {
        var total = Math.max(0, Math.floor(Number(seconds) || 0))
        var minutes = Math.floor(total / 60)
        var remaining = total % 60
        return minutes + ":" + (remaining < 10 ? "0" : "") + remaining
    }
}
