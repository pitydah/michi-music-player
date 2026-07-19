import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "albumDetailPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Detalle de álbum")

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property string albumGenre: ""
    property string albumCoverKey: ""
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var albumTracks: []
    property bool loading: false

    function routeEnter(route, params) {
        if (params && params.album_key) root.loadAlbum(params.album_key)
    }

    function routeParamsChanged(route, params) {
        if (params && params.album_key && params.album_key !== root.albumKey)
            root.loadAlbum(params.album_key)
    }

    function loadAlbum(key) {
        if (!key || !root.lib) return
        root.loading = true
        root.albumKey = key
        root.albumCoverKey = key
        var detail = root.lib.getAlbumDetail ? root.lib.getAlbumDetail(key) : null
        if (detail && detail.ok) {
            root.albumTitle = detail.title || detail.album || key
            root.albumArtist = detail.artist || detail.album_artist || ""
            root.albumYear = Number(detail.year || 0)
            root.albumGenre = detail.genre || ""
            root.albumCoverKey = detail.cover_key || detail.album_key || key
        } else {
            root.albumTitle = key
        }
        root.albumTracks = root.lib.getAlbumTracks ? root.lib.getAlbumTracks(key) : []
        root.loading = false
    }

    function totalDuration() {
        var total = 0
        for (var i = 0; i < root.albumTracks.length; i++)
            total += Number(root.albumTracks[i].duration || 0)
        return total
    }

    function playShuffled() {
        if (!root.lib || root.albumTracks.length === 0) return
        var shuffled = root.albumTracks.slice()
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

    function formatDuration(seconds) {
        var value = Math.max(0, Number(seconds || 0))
        var hours = Math.floor(value / 3600)
        var minutes = Math.floor((value % 3600) / 60)
        var secs = Math.floor(value % 60)
        if (hours > 0)
            return hours + ":" + (minutes < 10 ? "0" : "") + minutes + ":" + (secs < 10 ? "0" : "") + secs
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
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: qsTr("← Volver")
                    variant: "ghost"
                    onClicked: {
                        if (typeof navigationBridge !== "undefined") navigationBridge.back()
                    }
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: root.albumTracks.length + " " + qsTr("canciones") + " · " + root.formatDuration(root.totalDuration())
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 270
                radius: MichiTheme.radius.xl
                color: MichiTheme.colors.surfaceHero
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderSubtle
                clip: true

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: MichiTheme.colors.accentSoft }
                        GradientStop { position: 0.65; color: "transparent" }
                        GradientStop { position: 1.0; color: MichiTheme.colors.surfaceSubtle }
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.xl

                    CoverImage {
                        Layout.preferredWidth: 210
                        Layout.preferredHeight: 210
                        coverRadius: MichiTheme.radius.lg
                        coverKey: root.albumCoverKey || root.albumKey
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: qsTr("ÁLBUM")
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.captionSize
                            font.weight: MichiTheme.typography.weightBold
                            font.letterSpacing: 1.4
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.albumTitle || qsTr("Álbum sin título")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.albumArtist || qsTr("Artista desconocido")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            elide: Text.ElideRight
                        }
                        Text {
                            text: ((root.albumYear > 0) ? root.albumYear + " · " : "") +
                                  (root.albumGenre ? root.albumGenre + " · " : "") +
                                  root.albumTracks.length + " " + qsTr("canciones")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm
                            MichiButton {
                                text: qsTr("Reproducir")
                                variant: "primary"
                                enabled: root.albumTracks.length > 0
                                onClicked: root.lib.playAlbum(root.albumKey)
                            }
                            MichiButton {
                                text: qsTr("Mezclar")
                                variant: "ghost"
                                enabled: root.albumTracks.length > 0
                                onClicked: root.playShuffled()
                            }
                            MichiButton {
                                text: qsTr("Añadir a cola")
                                variant: "ghost"
                                enabled: root.albumTracks.length > 0
                                onClicked: root.lib.enqueueAlbum(root.albumKey)
                            }
                        }
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
                Layout.preferredHeight: Math.max(180, Math.min(620, root.albumTracks.length * 46 + 12))
                radius: MichiTheme.radius.lg
                color: MichiTheme.colors.surfaceCard
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderCard
                clip: true

                ListView {
                    id: tracksList
                    anchors.fill: parent
                    anchors.margins: 6
                    model: root.albumTracks
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    activeFocusOnTab: true
                    focus: true
                    keyNavigationWraps: false
                    ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

                    Keys.onReturnPressed: {
                        if (currentIndex >= 0) root.lib.playTrackById(root.albumTracks[currentIndex].track_id || 0)
                    }
                    Keys.onEnterPressed: {
                        if (currentIndex >= 0) root.lib.playTrackById(root.albumTracks[currentIndex].track_id || 0)
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
                                text: modelData.track_number || (index + 1)
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                horizontalAlignment: Text.AlignRight
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.title || qsTr("Canción sin título")
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightMedium
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.artist || root.albumArtist
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                    elide: Text.ElideRight
                                }
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
        title: qsTr("Cargando álbum")
    }
}
