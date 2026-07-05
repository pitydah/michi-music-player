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
    property var bridge: null
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var np: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var _tracks: []

    signal backRequested()

    function loadAlbum(key, title, artist, year) {
        albumKey = key; albumTitle = title; albumArtist = artist; albumYear = year
        if (root.lib && root.lib.trackModel) {
            root.lib.trackModel.refresh(album: key, sort: "track_number", asc: true)
        }
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            MichiButton { text: "← Volver"; variant: "ghost"; onClicked: root.backRequested() }

            Row {
                width: parent.width; spacing: MichiTheme.spacing.xl

                CoverImage { width: 160; height: 160; coverRadius: MichiTheme.radiusSm; coverKey: root.albumKey || "ALBUM" }

                Column {
                    anchors.verticalCenter: parent.verticalCenter; spacing: MichiTheme.spacing.sm

                    Text { text: root.albumTitle; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: FontWeight.Bold; wrapMode: Text.WordWrap; width: parent.width }
                    Text { text: root.albumArtist; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.sectionTitleSize; visible: root.albumArtist !== "" }
                    Text { text: root.albumYear > 0 ? root.albumYear : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; visible: text !== "" }
                    Text { text: "Canciones: " + (root.lib && root.lib.trackModel ? root.lib.trackModel.totalCount : 0); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }

                    RowLayout { spacing: MichiTheme.spacing.sm
                        MichiButton { text: "Reproducir"; variant: "primary"; onClicked: { if (root.lib && root.lib.trackModel && root.lib.trackModel.count > 0 && root.np) root.np.next() } }
                        MichiButton { text: "Mezclar"; variant: "ghost"; onClicked: {} }
                    }
                }
            }

            SectionHeader { text: "Canciones"; width: parent.width }

            ListView {
                width: parent.width; height: 400; clip: true; boundsBehavior: Flickable.StopAtBounds
                model: root.lib ? root.lib.trackModel : []

                delegate: Item {
                    width: parent.width; height: 36
                    RowLayout { anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { text: (typeof trackNumber !== "undefined" ? trackNumber : "") || ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; width: 30 }
                        Text { text: title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: duration ? formatDuration(duration) : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { if (root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) } }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
