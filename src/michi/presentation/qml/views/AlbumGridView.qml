import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../media"
import "../theme"

GridView {
    id: albumGrid
    objectName: "albumGridView"

    property var albumModel: library.albums
    readonly property int minimumCardWidth: MichiThemeState.density === "compact"
        ? 148 : MichiThemeState.density === "comfortable" ? 212 : 178
    readonly property int columnCount: Math.max(1, Math.floor(width / minimumCardWidth))

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    cellWidth: width / columnCount
    cellHeight: Math.min(292, Math.max(194, cellWidth + (
        MichiThemeState.density === "compact" ? 42 : 58)))
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    cacheBuffer: cellHeight * 2
    Accessible.role: Accessible.List
    Accessible.name: "Albums in grid view"
    Accessible.description: "Use arrow keys to browse and Enter to open an album"

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Home) {
            currentIndex = count > 0 ? 0 : -1
            positionViewAtBeginning()
            event.accepted = true
        } else if (event.key === Qt.Key_End) {
            currentIndex = count > 0 ? count - 1 : -1
            positionViewAtEnd()
            event.accepted = true
        }
    }

    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        width: MichiSpacing.sm
    }

    delegate: AlbumCard {
        required property int index
        required property var modelData
        width: albumGrid.cellWidth - MichiThemeState.contentGap
        height: albumGrid.cellHeight - MichiThemeState.contentGap
        album: modelData
        selected: GridView.isCurrentItem
        onActiveFocusChanged: {
            if (activeFocus)
                albumGrid.currentIndex = index
        }
        onActivated: {
            albumGrid.currentIndex = index
            library.select_album(modelData.key)
        }
    }
}
