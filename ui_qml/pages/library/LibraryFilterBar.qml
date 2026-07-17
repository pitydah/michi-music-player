import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Filter Bar"
    objectName: "libraryFilterBar"
    focus: true
    id: root
    width: parent.width; height: MichiTheme.rowHeightCompact

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

        FilterChip { objectName: "filterChipTodos"; text: "Todos"; selected: !root.lib || root.lib.activeFormatFilter === ""; onClicked: root.formatFilterChanged("") }
        FilterChip { objectName: "filterChipFlac"; text: "FLAC"; selected: root.lib && root.lib.activeFormatFilter === "flac"; onClicked: root.formatFilterChanged("flac") }
        FilterChip { objectName: "filterChipMp3"; text: "MP3"; selected: root.lib && root.lib.activeFormatFilter === "mp3"; onClicked: root.formatFilterChanged("mp3") }
        FilterChip { objectName: "filterChipWav"; text: "WAV"; selected: root.lib && root.lib.activeFormatFilter === "wav"; onClicked: root.formatFilterChanged("wav") }
        FilterChip { objectName: "filterChipDsd"; text: "DSD"; selected: root.lib && root.lib.activeFormatFilter === "dsd"; onClicked: root.formatFilterChanged("dsd") }
        FilterChip { objectName: "filterChipFavorites"; text: "Favoritos"; selected: false; onClicked: { if (root.lib) root.lib.setFavoritesFilter() } }
        FilterChip { objectName: "filterChipUnplayed"; text: "No reproducidos"; selected: false; onClicked: { if (root.lib) root.lib.setUnplayedFilter() } }
    }
}
