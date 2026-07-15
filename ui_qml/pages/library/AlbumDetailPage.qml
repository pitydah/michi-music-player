import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property string albumGenre: ""
    property string albumCoverKey: ""
    property var bridge: null
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var _tracks: []
    property int _selectedDisc: -1
    property int _discCount: 1
    property bool _compilation: false
    property bool _backState: false
    property int _missingCount: 0
    property bool _loadingDetail: false
    property string _errorMessage: ""

    signal backRequested()

    objectName: "albumDetail.page"
    Accessible.role: Accessible.Panel
    Accessible.name: "Detalle del álbum"
    Accessible.description: albumTitle + " por " + albumArtist

    function loadAlbum(key, title, artist, year) {
        albumKey = key; albumTitle = title; albumArtist = artist; albumYear = year
        albumCoverKey = key
        root._selectedDisc = -1
        root._discCount = 1
        root._compilation = false
        root._missingCount = 0
        root._loadingDetail = true
        root._errorMessage = ""
        if (root.lib && root.lib.getAlbumDetail) {
            try {
                var detail = root.lib.getAlbumDetail(key)
                if (detail && detail.ok) {
                    albumGenre = detail.genre || ""
                    root._discCount = detail.disc_count > 1 ? detail.disc_count : 1
                    root._compilation = detail.compilation || false
                    root._missingCount = detail.missing_count || 0
                } else {
                    root._errorMessage = (detail && detail.error) || "Error al cargar detalle"
                }
            } catch (e) {
                root._errorMessage = "Error: " + e
            }
        }
        root._loadingDetail = false
        if (root.lib && root.lib.getAlbumTracks) {
            try {
                root._tracks = root.lib.getAlbumTracks(key)
            } catch (e) {
                root._errorMessage = "Error al cargar pistas: " + e
                root._tracks = []
            }
        }
    }

    function playDisc(discNum) {
        if (!root.lib || !root._tracks.length) return
        var discTracks = []
        for (var i = 0; i < root._tracks.length; i++) {
            var t = root._tracks[i]
            if (discNum <= 0 || t.disc_number === discNum) {
                discTracks.push(t)
            }
        }
        if (discTracks.length > 0 && root.lib && root.lib.playTrackById)
            root.lib.playTrackById(discTracks[0].track_id)
        for (var j = 1; j < discTracks.length; j++) {
            if (root.lib && root.lib.enqueueTrackById)
                root.lib.enqueueTrackById(discTracks[j].track_id)
        }
    }

    function queueAlbum() {
        if (root.lib) root.lib.enqueueAlbum(root.albumKey)
    }

    function playAlbum() {
        if (root.lib) root.lib.playAlbum(root.albumKey)
    }

    function playDiscTracks(discNum) {
        if (!root.lib || !root._tracks.length) return
        var discTracks = []
        for (var i = 0; i < root._tracks.length; i++) {
            var t = root._tracks[i]
            if (discNum <= 0 || t.disc_number === discNum) {
                discTracks.push(t)
            }
        }
        if (discTracks.length > 0 && root.lib && root.lib.enqueueTrackById)
            root.lib.enqueueTrackById(discTracks[0].track_id)
        for (var j = 1; j < discTracks.length; j++) {
            if (root.lib && root.lib.enqueueTrackById)
                root.lib.enqueueTrackById(discTracks[j].track_id)
        }
    }

    function tracksForDisc(discNum) {
        if (discNum <= 0) return root._tracks
        var result = []
        for (var i = 0; i < root._tracks.length; i++) {
            if (root._tracks[i].disc_number === discNum)
                result.push(root._tracks[i])
        }
        return result
    }

    Flickable {
        anchors.fill: parent
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds
        objectName: "albumDetail.flickable"

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Escape) root.backRequested()
        }

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            RowLayout {
                width: parent.width; spacing: MichiTheme.spacing.sm
                anchors.margins: MichiTheme.spacing.md

                MichiButton {
                    text: "← Volver"; variant: "ghost"
                    objectName: "albumDetail.backButton"
                    Accessible.name: "Volver a álbumes"
                    onClicked: root.backRequested()
                    KeyNavigation.tab: playAlbumBtn
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 200
                    color: "transparent"

                    Row {
                        anchors.fill: parent; spacing: MichiTheme.spacing.xl
                        anchors.margins: MichiTheme.spacing.md

                        CoverImage {
                            width: 160; height: 160; coverRadius: MichiTheme.radiusSm
                            coverKey: root.albumCoverKey || root.albumKey || "ALBUM"
                            objectName: "albumDetail.cover"
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: MichiTheme.spacing.sm
                            width: parent.width - 180

                            Text {
                                text: root.albumTitle
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.heroTitleSize
                                font.weight: MichiTheme.typography.weightBold
                                wrapMode: Text.WordWrap; width: parent.width
                                Accessible.name: "Álbum: " + root.albumTitle
                            }

                            Text {
                                text: root.albumArtist
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.sectionTitleSize
                                visible: root.albumArtist !== ""
                                Accessible.name: "Artista: " + root.albumArtist
                            }

                            Row {
                                spacing: MichiTheme.spacing.sm
                                Text {
                                    text: root.albumYear > 0 ? root.albumYear : ""
                                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                                    visible: text !== ""
                                }
                                Text {
                                    text: root.albumGenre
                                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                                    visible: text !== ""
                                }
                                Text {
                                    text: root._compilation ? "Compilación" : ""
                                    color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize
                                    visible: root._compilation
                                }
                            }

                            Text {
                                text: "Canciones: " + root._tracks.length +
                                      (root._discCount > 1 ? " · " + root._discCount + " discos" : "") +
                                      (root._missingCount > 0 ? " · " + root._missingCount + " faltantes" : "")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            RowLayout {
                                spacing: MichiTheme.spacing.sm
                                MichiButton {
                                    id: playAlbumBtn
                                    text: "Reproducir"; variant: "primary"
                                    objectName: "albumDetail.playButton"
                                    Accessible.name: "Reproducir álbum"
                                    onClicked: root.playAlbum()
                                    KeyNavigation.tab: shuffleBtn
                                }
                                MichiButton {
                                    id: shuffleBtn
                                    text: "Mezclar"; variant: "ghost"
                                    objectName: "albumDetail.shuffleButton"
                                    Accessible.name: "Mezclar álbum"
                                    onClicked: {
                                        if (root.lib && root.lib.getAlbumTracks) {
                                            var allTracks = root.lib.getAlbumTracks(root.albumKey)
                                            if (allTracks.length > 0 && root.lib && root.lib.playTrackById)
                                                root.lib.playTrackById(allTracks[0].track_id)
                                        }
                                    }
                                    KeyNavigation.tab: queueAlbumBtn
                                }
                                MichiButton {
                                    id: queueAlbumBtn
                                    text: "Añadir a cola"; variant: "ghost"
                                    objectName: "albumDetail.queueButton"
                                    Accessible.name: "Añadir álbum a la cola"
                                    onClicked: root.queueAlbum()
                                    KeyNavigation.tab: addPlaylistBtn
                                }
                                MichiButton {
                                    id: addPlaylistBtn
                                    text: "Añadir a playlist"; variant: "ghost"
                                    objectName: "albumDetail.addToPlaylistButton"
                                    Accessible.name: "Añadir a playlist"
                                    onClicked: {
                                        if (typeof navigationBridge !== "undefined")
                                            navigationBridge.navigate("playlists")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item {
                width: parent.width
                height: 24
                visible: root._loadingDetail
                BusyIndicator {
                    anchors.centerIn: parent
                    running: true
                }
            }

            Item {
                width: parent.width
                height: 24
                visible: root._errorMessage !== ""
                Text {
                    anchors.centerIn: parent
                    text: root._errorMessage
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            SectionHeader {
                text: "Canciones"
                width: parent.width
                objectName: "albumDetail.sectionHeader"
            }

            Row {
                width: parent.width; spacing: MichiTheme.spacing.sm
                leftPadding: MichiTheme.spacing.md; bottomPadding: MichiTheme.spacing.sm
                visible: root._discCount > 1

                Repeater {
                    model: root._discCount
                    delegate: MichiButton {
                        text: "Disco " + (modelData + 1)
                        variant: root._selectedDisc === (modelData + 1) ? "primary" : "ghost"
                        height: 24
                        objectName: "albumDetail.discButton." + (modelData + 1)
                        Accessible.name: "Disco " + (modelData + 1)
                        onClicked: {
                            root._selectedDisc = (root._selectedDisc === (modelData + 1)) ? -1 : (modelData + 1)
                        }
                    }
                }
            }

            ListView {
                id: tracksList
                width: parent.width
                height: Math.min(600, visibleTracks.length * 36)
                clip: true; boundsBehavior: Flickable.StopAtBounds
                model: visibleTracks
                objectName: "albumDetail.tracksList"
                keyNavigationWraps: false

                property var visibleTracks: {
                    if (root._selectedDisc > 0)
                        return root.tracksForDisc(root._selectedDisc)
                    return root._tracks
                }

                ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

                delegate: Item {
                    width: parent.width; height: 36
                    objectName: "albumDetail.trackRow." + index
                    Accessible.role: Accessible.ListItem
                    Accessible.name: (modelData.title || "") + " - " + (modelData.artist || "")

                    Rectangle {
                        anchors.fill: parent
                        color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                            anchors.rightMargin: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.sm

                            Text {
                                text: typeof modelData.track_number !== "undefined" && modelData.track_number > 0 ? modelData.track_number : ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: 30
                            }

                            Column {
                                Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                                Text {
                                    text: modelData.title || ""
                                    color: modelData.missing ? MichiTheme.colors.textDisabled : MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    elide: Text.ElideRight; width: parent.width
                                    font.italic: modelData.missing
                                }
                                Text {
                                    text: modelData.artist || ""
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                    elide: Text.ElideRight; width: parent.width
                                    visible: text !== "" && text !== root.albumArtist && root._compilation
                                }
                            }

                            TrackQualityBadge {
                                format: modelData.format || ""
                                bitDepth: modelData.bit_depth || 0
                                visible: !modelData.missing
                            }

                            Text {
                                text: modelData.missing ? "Faltante" : (modelData.duration ? formatDuration(modelData.duration) : "")
                                color: modelData.missing ? MichiTheme.colors.error : MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                font.italic: modelData.missing
                            }
                        }

                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (!modelData.missing && root.lib && root.lib.playTrackById)
                                    root.lib.playTrackById(modelData.track_id || 0)
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width; height: 40
                color: "transparent"
                visible: root._missingCount > 0

                Row {
                    anchors.centerIn: parent; spacing: MichiTheme.spacing.sm
                    Text {
                        text: root._missingCount + " pista(s) faltante(s). Usa Library Doctor para localizar."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                    MichiButton { text: "Library Doctor"; variant: "ghost"; height: 24; onClicked: {
                        if (typeof navigationBridge !== "undefined") navigationBridge.navigate("library_doctor")
                    }}
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}