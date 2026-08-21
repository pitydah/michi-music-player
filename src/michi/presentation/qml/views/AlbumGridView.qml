import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../media"
import "../theme"

GridView {
    id: albumGrid
    objectName: "albumGridView"

    property var albumModel: library.albums
    property real albumZoom: 1.0
    readonly property int minimumCardWidth: MichiThemeState.density === "compact"
        ? Math.round(154 * albumZoom)
        : MichiThemeState.density === "comfortable"
            ? Math.round(220 * albumZoom) : Math.round(184 * albumZoom)
    readonly property int maximumCardWidth: MichiThemeState.density === "compact"
        ? Math.round(184 * albumZoom)
        : MichiThemeState.density === "comfortable"
            ? Math.round(250 * albumZoom) : Math.round(216 * albumZoom)
    readonly property int cardGap: MichiThemeState.contentGap
    readonly property int columnCount: Math.max(1, Math.floor(
        (width + cardGap) / (minimumCardWidth + cardGap)))
    readonly property real resolvedCardWidth: Math.min(maximumCardWidth,
        cellWidth - cardGap)
    readonly property int metadataHeight: MichiThemeState.density === "compact"
        ? 76 : MichiThemeState.density === "comfortable" ? 108 : 92

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    cellWidth: width / columnCount
    cellHeight: resolvedCardWidth + metadataHeight + cardGap
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

    delegate: Item {
        id: albumCell
        required property int index
        required property var modelData
        readonly property bool current: GridView.isCurrentItem

        width: albumGrid.cellWidth
        height: albumGrid.cellHeight

        AlbumCard {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: albumGrid.resolvedCardWidth
            height: parent.height - albumGrid.cardGap
            album: albumCell.modelData
            selected: albumCell.current
            onActiveFocusChanged: {
                if (activeFocus)
                    albumGrid.currentIndex = albumCell.index
            }
            onActivated: {
                albumGrid.currentIndex = albumCell.index
                library.select_album(albumCell.modelData.key)
            }
        }
    }
}
