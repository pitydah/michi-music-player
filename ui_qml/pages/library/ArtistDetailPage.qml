import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Artist Detail"
    objectName: "artistDetailPage"
    focus: true
    id: root

    property string artistName: ""
    property var bridge: null
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var artistAlbums: []
    property int artistTrackCount: 0
    property int artistAlbumCount: 0
    property string artistGenre: ""

    signal backRequested()

    function loadArtist(name) {
        artistName = name
        if (root.lib && root.lib.trackModel) {
            root.lib.trackModel.refresh("artist", name, "year", true)
        }
        if (root.lib && root.lib.albumModel) {
            root.lib.albumModel.refresh("search", name, "", false)
        }
        if (root.lib && root.lib.getArtistDetail) {
            var detail = root.lib.getArtistDetail(name)
            if (detail && detail.ok) {
                artistAlbumCount = detail.album_count || 0
                artistTrackCount = detail.track_count || 0
                artistGenre = detail.genre || ""
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            RowLayout {
                width: parent.width; spacing: MichiTheme.spacing.sm
                anchors.margins: MichiTheme.spacing.md

                MichiButton { text: "← Volver"; variant: "ghost"; onClicked: root.backRequested() }

                Rectangle {
                    width: 48; height: 48; radius: 24
                    color: MichiTheme.colors.surfaceCard
                    Text {
                        anchors.centerIn: parent
                        text: root.artistName.length > 0 ? root.artistName.charAt(0).toUpperCase() : "?"
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: 22; font.weight: MichiTheme.typography.weightBold
                    }
                }

                Column {
                    Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                    Text {
                        text: root.artistName
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: FontWeight.Bold
                        elide: Text.ElideRight; width: parent.width
                    }
                    Text {
                        text: root.artistAlbumCount + " álbumes · " + root.artistTrackCount + " canciones" +
                              (root.artistGenre ? " · " + root.artistGenre : "")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                }
            }

            RowLayout {
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Reproducir todo"; variant: "primary"; onClicked: { if (root.lib) root.lib.playArtist(root.artistName) } }
                MichiButton { text: "Mezclar"; variant: "ghost" }
                MichiButton { text: "Añadir a cola"; variant: "ghost"; onClicked: {
                    if (root.lib && root.lib.trackModel) {
                        root.lib.trackModel.refresh("artist", root.artistName, "", false)
                    }
                }}
            }

            SectionHeader { text: "Álbumes"; width: parent.width }

            ListView {
                width: parent.width
                height: Math.min(300, (root.lib && root.lib.albumModel ? root.lib.albumModel.count : 0) * 56)
                clip: true; boundsBehavior: Flickable.StopAtBounds
                model: root.lib ? root.lib.albumModel : []

                delegate: Item {
                    width: parent.width; height: 56
                    RowLayout {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.md

                        CoverImage { width: 40; height: 40; coverRadius: 4; coverKey: albumKey || "" }

                        Column { Layout.fillWidth: true
                            Text {
                                text: title || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight; width: parent.width
                            }
                            Text {
                                text: (year > 0 ? year + " · " : "") + (trackCount || 0) + " temas"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                        }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor }
                }
            }

            SectionHeader { text: "Canciones"; width: parent.width }

            ListView {
                width: parent.width
                height: Math.min(400, (root.lib && root.lib.trackModel ? root.lib.trackModel.count : 0) * 36)
                clip: true; boundsBehavior: Flickable.StopAtBounds
                model: root.lib ? root.lib.trackModel : []

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
                            text: album || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            Layout.preferredWidth: 150; elide: Text.ElideRight
                        }
                        Text {
                            text: duration ? formatDuration(duration) : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: { if (root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) }
                    }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
