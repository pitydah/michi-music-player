import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    width: parent.width; height: 30

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null

    signal formatFilterChanged(string fmt)
    signal genreFilterChanged(string genre)
    signal yearFilterChanged(string year)

    function clearAll() { formatChips.clear(); genreChips.clear(); yearChips.clear() }

    Flow {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.xs
        visible: true

        FilterChip { text: "Todos"; selected: !root.lib || root.lib.activeFormatFilter === ""; onClicked: root.formatFilterChanged("") }
        FilterChip { text: "FLAC"; selected: root.lib && root.lib.activeFormatFilter === "flac"; onClicked: root.formatFilterChanged("flac") }
        FilterChip { text: "MP3"; selected: root.lib && root.lib.activeFormatFilter === "mp3"; onClicked: root.formatFilterChanged("mp3") }
        FilterChip { text: "WAV"; selected: root.lib && root.lib.activeFormatFilter === "wav"; onClicked: root.formatFilterChanged("wav") }
        FilterChip { text: "DSD"; selected: root.lib && root.lib.activeFormatFilter === "dsd"; onClicked: root.formatFilterChanged("dsd") }
        FilterChip { text: "Favoritos"; selected: false; onClicked: { if (root.lib) root.lib.setFavoritesFilter() } }
        FilterChip { text: "No reproducidos"; selected: false; onClicked: { if (root.lib) root.lib.setUnplayedFilter() } }
    }
}
