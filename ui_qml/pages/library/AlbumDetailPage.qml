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

    signal backRequested()

    function loadAlbum(key, title, artist, year) {
        albumKey = key; albumTitle = title; albumArtist = artist; albumYear = year
        albumCoverKey = key
        root._selectedDisc = -1
        root._discCount = 1
        root._compilation = false
        root._missingCount = 0
        if (root.lib && root.lib.trackModel) {
            root.lib.trackModel.refresh("album", key, "track_number", true)
        }
        if (root.lib && root.lib.getAlbumDetail) {
            var detail = root.lib.getAlbumDetail(key)
            if (detail && detail.ok) {
                albumGenre = detail.genre || ""
                root._discCount = detail.disc_count > 1 ? detail.disc_count : 1
                root._compilation = detail.compilation || false
                root._missingCount = detail.missing_count || 0
            }
        }
    }

    function playDisc(discNum) {
        if (!root.lib || !root.lib.trackModel) return
        var discIds = []
        for (var i = 0; i < root.lib.trackModel.count; i++) {
            var idx = root.lib.trackModel.index(i, 0)
            var disc = root.lib.trackModel.data(idx, 0x0110)
            if (disc === discNum || discNum <= 0) {
                discIds.push(root.lib.trackModel.data(idx, 0x0101))
            }
        }
        if (discIds.length > 0 && root.lib && root.lib.playTrackById)
            root.lib.playTrackById(discIds[0])
        for (var j = 1; j < discIds.length; j++) {
            if (root.lib && root.lib.enqueueTrackById)
                root.lib.enqueueTrackById(discIds[j])
        }
    }

    function queueAlbum() {
        if (root.lib) root.lib.enqueueAlbum(root.albumKey)
    }

    function playAlbum() {
        if (root.lib) root.lib.playAlbum(root.albumKey)
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
                            Text {
                                text: root._compilation ? "Compilación" : ""
                                color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize
                                visible: root._compilation
                            }
                        }

                        Text {
                            text: "Canciones: " + (root.lib && root.lib.trackModel ? root.lib.trackModel.totalCount : 0) +
                                  (root._discCount > 1 ? " · " + root._discCount + " discos" : "") +
                                  (root._missingCount > 0 ? " · " + root._missingCount + " faltantes" : "")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm
                            MichiButton { text: "Reproducir"; variant: "primary"; onClicked: root.playAlbum() }
                            MichiButton { text: "Mezclar"; variant: "ghost"; onClicked: {
                                if (root.lib && root.lib.trackModel) {
                                    root.lib.trackModel.refresh("album", root.albumKey, "random", true)
                                }
                            }}
                            MichiButton { text: "Añadir a cola"; variant: "ghost"; onClicked: root.queueAlbum() }
                            MichiButton { text: "Añadir a playlist"; variant: "ghost"; onClicked: {
                                if (typeof navigationBridge !== "undefined")
                                    navigationBridge.navigate("playlists")
                            }}
                        }
                    }
                }
            }

            SectionHeader { text: "Canciones"; width: parent.width }

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
                        onClicked: {
                            root._selectedDisc = (root._selectedDisc === (modelData + 1)) ? -1 : (modelData + 1)
                            root.playDisc(root._selectedDisc)
                        }
                    }
                }
            }

            ListView {
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
                                color: missing ? MichiTheme.colors.textDisabled : MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight; width: parent.width
                                font.italic: missing
                            }
                            Text {
                                text: artist || ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.captionSize
                                elide: Text.ElideRight; width: parent.width
                                visible: text !== "" && text !== root.albumArtist && root._compilation
                            }
                        }

                        TrackQualityBadge {
                            format: format || ""
                            bitDepth: bitDepth || 0
                            visible: !missing
                        }

                        Text {
                            text: missing ? "Faltante" : (duration ? formatDuration(duration) : "")
                            color: missing ? MichiTheme.colors.errorColor : MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.italic: missing
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { if (!missing && root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) }
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
