import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property string genre: ""
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null

    signal backRequested()

    function loadGenre(name) {
        genre = name
        if (root.lib && root.lib.setGenreFilter) {
            root.lib.setGenreFilter(name)
        }
    }

    ColumnLayout {
        anchors.fill: parent; spacing: MichiTheme.spacing.lg
        anchors.margins: MichiTheme.spacing.xl

        RowLayout { spacing: MichiTheme.spacing.sm
            MichiButton { text: "← Volver"; variant: "ghost"; onClicked: root.backRequested() }
            Text {
                text: "Género: " + root.genre
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.heroTitleSize
                font.weight: FontWeight.Bold
            }
        }

        RowLayout { spacing: MichiTheme.spacing.sm
            MichiButton { text: "Reproducir todo"; variant: "primary"; onClicked: { if (root.lib && root.lib.playAllFiltered) root.lib.playAllFiltered() } }
            MichiButton { text: "Mezclar"; variant: "ghost" }
            MichiButton { text: "Añadir a cola"; variant: "ghost" }
        }

        SectionHeader { text: "Canciones en " + root.genre; width: parent.width }

        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root.lib ? root.lib.trackModel : []
            clip: true; boundsBehavior: Flickable.StopAtBounds

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
                    onClicked: { if (root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
