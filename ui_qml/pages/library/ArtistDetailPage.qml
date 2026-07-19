import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "artistDetailPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Detalle de artista")

    property string artistName: ""
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var artistTracks: []
    property var artistAlbums: []
    property int artistTrackCount: 0
    property int artistAlbumCount: 0
    property string artistGenre: ""
    property bool loading: false

    function routeEnter(route, params) {
        if (params && params.artist) root.loadArtist(params.artist)
    }

    function routeParamsChanged(route, params) {
        if (params && params.artist && params.artist !== root.artistName)
            root.loadArtist(params.artist)
    }

    function loadArtist(name) {
        if (!name || !root.lib) return
        root.loading = true
        root.artistName = name
        var detail = root.lib.getArtistDetail ? root.lib.getArtistDetail(name) : null
        if (detail && detail.ok) {
            root.artistTrackCount = Number(detail.track_count || 0)
            root.artistAlbumCount = Number(detail.album_count || 0)
            root.artistGenre = detail.genre || ""
        }
        root.artistTracks = root.lib.getArtistTracks ? root.lib.getArtistTracks(name) : []
        root.artistAlbums = root.deriveAlbums(root.artistTracks)
        if (root.artistTrackCount <= 0) root.artistTrackCount = root.artistTracks.length
        if (root.artistAlbumCount <= 0) root.artistAlbumCount = root.artistAlbums.length
        root.loading = false
    }

    function deriveAlbums(tracks) {
        var seen = ({})
        var result = []
        for (var i = 0; i < tracks.length; i++) {
            var track = tracks[i]
            var key = track.album_key || track.album || ""
            if (!key || seen[key]) continue
            seen[key] = true
            result.push({
                albumKey: key,
                title: track.album || key,
                artist: track.album_artist || track.artist || root.artistName,
                year: Number(track.year || 0),
                coverKey: track.cover_key || key
            })
        }
        result.sort(function(a, b) { return Number(b.year || 0) - Number(a.year || 0) })
        return result
    }

    function playShuffled() {
        if (!root.lib || root.artistTracks.length === 0) return
        var shuffled = root.artistTracks.slice()
        for (var i = shuffled.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1))
            var tmp = shuffled[i]
            shuffled[i] = shuffled[j]
            shuffled[j] = tmp
        }
        root.lib.playTrackById(shuffled[0].track_id || 0)
        for (var q = 1; q < shuffled.length; q++)
            root.lib.enqueueTrackById(shuffled[q].track_id || 0)
    }

    function enqueueAll() {
        for (var i = 0; i < root.artistTracks.length; i++)
            root.lib.enqueueTrackById(root.artistTracks[i].track_id || 0)
    }

    function formatDuration(seconds) {
        var value = Math.max(0, Number(seconds || 0))
        var minutes = Math.floor(value / 60)
        var secs = Math.floor(value % 60)
        return minutes + ":" + (secs < 10 ? "0" : "") + secs
    }

    Flickable {
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: contentColumn.height + MichiTheme.spacing.xl
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            RowLayout {
                Layout.fillWidth: true
                MichiButton {
                    text: qsTr("← Volver")
                    variant: "ghost"
                    onClicked: {
                        if (typeof navigationBridge !== "undefined") navigationBridge.back()
                    }
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: root.artistAlbumCount + " " + qsTr("álbumes") + " · " +
                          root.artistTrackCount + " " + qsTr("canciones")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 250
                radius: MichiTheme.radius.xl
                color: MichiTheme.colors.surfaceHero
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderSubtle
                clip: true

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: MichiTheme.colors.accentSoft }
                        GradientStop { position: 0.7; color: "transparent" }
                        GradientStop { position: 1.0; color: MichiTheme.colors.surfaceSubtle }
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.xl

                    Rectangle {
                        Layout.preferredWidth: 176
                        Layout.preferredHeight: 176
                        radius: 88
                        color: MichiTheme.colors.surfaceElevation3
                        border.width: MichiTheme.borderWidthFocus
                        border.color: MichiTheme.colors.borderActive

                        Text {
                            anchors.centerIn: parent
                            text: root.artistName.length > 0 ? root.artistName.charAt(0).toUpperCase() : "?"
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: 64
                            font.weight: MichiTheme.typography.weightBold
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: qsTr("ARTISTA")
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.captionSize
                            font.weight: MichiTheme.typography.weightBold
                            font.letterSpacing: 1.4
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.artistName || qsTr("Artista desconocido")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            elide: Text.ElideRight
                        }
                        Text {
                            text: root.artistAlbumCount + " " + qsTr("álbumes") + " · " +
                                  root.artistTrackCount + " " + qsTr("canciones") +
                                  (root.artistGenre ? " · " + root.artistGenre : "")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm
                            MichiButton {
                                text: qsTr("Reproducir todo")
                                variant: "primary"
                                enabled: root.artistTracks.length > 0
                                onClicked: root.lib.playArtist(root.artistName)
                            }
                            MichiButton {
                                text: qsTr("Mezclar")
                                variant: "ghost"
                                enabled: root.artistTracks.length > 0
                                onClicked: root.playShuffled()
                            }
                            MichiButton {
                                text: qsTr("Añadir a cola")
                                variant: "ghost"
                                enabled: root.artistTracks.length > 0
                                onClicked: root.enqueueAll()
                            }
                        }
                    }
                }
            }

            Text {
                text: qsTr("Álbumes")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            ListView {
                id: albumsRail
                Layout.fillWidth: true
                Layout.preferredHeight: root.artistAlbums.length > 0 ? 208 : 0
                orientation: ListView.Horizontal
                model: root.artistAlbums
                spacing: MichiTheme.spacing.md
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                snapMode: ListView.SnapToItem
                ScrollBar.horizontal: ScrollBar { height: 6; policy: ScrollBar.AsNeeded }

                delegate: Rectangle {
                    required property int index
                    required property var modelData
                    width: 160
                    height: 196
                    radius: MichiTheme.radius.lg
                    color: albumMouse.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                    border.width: MichiTheme.borderWidth
                    border.color: albumMouse.containsMouse ? MichiTheme.colors.borderHover : MichiTheme.colors.borderCard

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.xs
                        CoverImage {
                            Layout.fillWidth: true
                            Layout.preferredHeight: width
                            coverRadius: MichiTheme.radius.md
                            coverKey: modelData.coverKey || modelData.albumKey || ""
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.title || qsTr("Álbum sin título")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightSemiBold
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: (modelData.year || 0) > 0 ? modelData.year : qsTr("Sin año")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                        }
                    }

                    MouseArea {
                        id: albumMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof navigationBridge !== "undefined")
                                navigationBridge.navigateWithParams("library.album_detail", {album_key: modelData.albumKey})
                        }
                        onDoubleClicked: root.lib.playAlbum(modelData.albumKey)
                    }
                }
            }

            Text {
                text: qsTr("Canciones")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(180, Math.min(620, root.artistTracks.length * 46 + 12))
                radius: MichiTheme.radius.lg
                color: MichiTheme.colors.surfaceCard
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderCard
                clip: true

                ListView {
                    id: tracksList
                    anchors.fill: parent
                    anchors.margins: 6
                    model: root.artistTracks
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    activeFocusOnTab: true
                    focus: true
                    ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

                    Keys.onReturnPressed: {
                        if (currentIndex >= 0) root.lib.playTrackById(root.artistTracks[currentIndex].track_id || 0)
                    }
                    Keys.onEnterPressed: {
                        if (currentIndex >= 0) root.lib.playTrackById(root.artistTracks[currentIndex].track_id || 0)
                    }

                    delegate: Rectangle {
                        required property int index
                        required property var modelData
                        width: tracksList.width
                        height: 44
                        radius: MichiTheme.radius.sm
                        color: ListView.isCurrentItem
                               ? MichiTheme.colors.accentSelection
                               : trackMouse.containsMouse
                                 ? MichiTheme.colors.surfaceHover
                                 : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: MichiTheme.spacing.md
                            anchors.rightMargin: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.md

                            Text {
                                Layout.preferredWidth: 30
                                text: index + 1
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.title || qsTr("Canción sin título")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.preferredWidth: 180
                                text: modelData.album || qsTr("Sin álbum")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight
                            }
                            TrackQualityBadge {
                                format: modelData.format || ""
                                bitDepth: modelData.bit_depth || 0
                            }
                            Text {
                                Layout.preferredWidth: 52
                                text: root.formatDuration(modelData.duration || 0)
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        MouseArea {
                            id: trackMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onPressed: tracksList.currentIndex = index
                            onDoubleClicked: root.lib.playTrackById(modelData.track_id || 0)
                        }
                    }
                }
            }
        }
    }

    LoadingState {
        anchors.centerIn: parent
        visible: root.loading
        title: qsTr("Cargando artista")
    }
}
