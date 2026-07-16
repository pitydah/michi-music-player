import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Detail"
    objectName: "albumDetailPage"
    focus: true
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

    signal backRequested()

    function loadAlbum(key, title, artist, year) {
        albumKey = key; albumTitle = title; albumArtist = artist; albumYear = year
        albumCoverKey = key
        if (root.lib && root.lib.trackModel) {
            root.lib.trackModel.refreshForAlbum(key)
        }
        if (root.lib && root.lib.getAlbumDetail) {
            var detail = root.lib.getAlbumDetail(key)
            if (detail && detail.ok) {
                albumGenre = detail.genre || ""
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            MichiButton { text: "← Volver"; variant: "ghost"; onClicked: root.backRequested() }

            Rectangle {
                width: parent.width; height: 200
                color: "transparent"

                Row {
                    anchors.fill: parent; spacing: MichiTheme.spacing.xl
                    anchors.margins: MichiTheme.spacing.md

                    CoverImage {
                        width: 160; height: 160; coverRadius: MichiTheme.radiusSm
                        coverKey: root.albumCoverKey || root.albumKey || "ALBUM"
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: MichiTheme.spacing.sm
                        width: parent.width - 180

                        Text {
                            text: root.albumTitle
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: FontWeight.Bold
                            wrapMode: Text.WordWrap; width: parent.width
                        }

                        Text {
                            text: root.albumArtist
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            visible: root.albumArtist !== ""
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
                        }

                        Text {
                            text: "Canciones: " + (root.lib && root.lib.trackModel ? root.lib.trackModel.totalCount : 0)
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm
                            MichiButton { text: "Reproducir"; variant: "primary"; onClicked: { if (root.lib) root.lib.playAlbum(root.albumKey) } }
                            MichiButton { text: "Mezclar"; variant: "ghost"; onClicked: {
                                if (root.lib && root.lib.trackModel) {
                                    root.lib.trackModel.refreshForAlbum(root.albumKey)
                                }
                            }}
                            MichiButton { text: "Añadir a cola"; variant: "ghost"; onClicked: { if (root.lib) root.lib.enqueueAlbum(root.albumKey) } }
                        }
                    }
                }
            }

            SectionHeader { text: "Canciones"; width: parent.width }

            ListView {
                Accessible.role: Accessible.List

                Accessible.name: "ListView"

                activeFocusOnTab: true

                focusPolicy: Qt.StrongFocus
                id: tracksList
                width: parent.width
                height: Math.min(600, (root.lib && root.lib.trackModel ? root.lib.trackModel.count : 0) * 36)
                clip: true; boundsBehavior: Flickable.StopAtBounds
                model: root.lib ? root.lib.trackModel : []

                delegate: Item {
                    width: parent.width; height: 36
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: typeof trackNumber !== "undefined" && trackNumber > 0 ? trackNumber : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: 30
                        }

                        Column {
                            Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                            Text {
                                text: title || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight; width: parent.width
                            }
                            Text {
                                text: artist || ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.captionSize
                                elide: Text.ElideRight; width: parent.width; visible: text !== "" && text !== root.albumArtist
                            }
                        }

                        TrackQualityBadge {
                            format: format || ""
                            bitDepth: 0
                        }

                        Text {
                            text: duration ? formatDuration(duration) : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { if (root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) }
                    }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
