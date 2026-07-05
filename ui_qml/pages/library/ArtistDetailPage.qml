import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string artistName: ""
    property var bridge: null
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var np: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var artistAlbums: []

    signal backRequested()

    function loadArtist(name) {
        artistName = name
        if (root.lib && root.lib.trackModel) {
            root.lib.trackModel.refresh(artist: name, sort: "year", asc: true)
        }
        if (root.lib && root.lib.albumModel) {
            root.lib.albumModel.refresh(search: name)
        }
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            RowLayout { spacing: MichiTheme.spacing.sm
                MichiButton { text: "← Volver"; variant: "ghost"; onClicked: root.backRequested() }
                Text { text: root.artistName; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: FontWeight.Bold; Layout.fillWidth: true; elide: Text.ElideRight }
            }

            RowLayout { spacing: MichiTheme.spacing.sm
                MichiButton { text: "Reproducir todo"; variant: "primary" }
                MichiButton { text: "Mezclar"; variant: "ghost" }
            }

            SectionHeader { text: "Álbumes"; width: parent.width }

            ListView {
                width: parent.width; height: 300; clip: true; boundsBehavior: Flickable.StopAtBounds
                model: root.lib ? root.lib.albumModel : []

                delegate: Item {
                    width: parent.width; height: 48
                    RowLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.md
                        CoverImage { width: 40; height: 40; coverRadius: 4; coverKey: albumKey || "" }
                        Column { Layout.fillWidth: true
                            Text { text: title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; elide: Text.ElideRight; width: parent.width }
                            Text { text: (year > 0 ? year + " · " : "") + (trackCount || 0) + " temas"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor }
                }
            }

            SectionHeader { text: "Canciones"; width: parent.width }

            ListView {
                width: parent.width; height: 400; clip: true; boundsBehavior: Flickable.StopAtBounds
                model: root.lib ? root.lib.trackModel : []

                delegate: Item {
                    width: parent.width; height: 36
                    RowLayout { anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { text: title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: album || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; Layout.preferredWidth: 150; elide: Text.ElideRight }
                        Text { text: duration ? formatDuration(duration) : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { if (root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) } }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
