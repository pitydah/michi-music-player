import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../theme"

GridView {
    id: albumGrid
    objectName: "albumGridView"

    property var albumModel: library.albums
    // M9-R3 CONVERGENCE SEAL: target del contexto por teclado — el
    // álbum del currentIndex (roving). El teclado vive en el VIEW, no en
    // los delegates (activeFocusOnTab false): Menu/Shift+F10 abren el
    // menú del álbum actual.
    property var contextAlbum: null

    function openCurrentAlbumContext() {
        if (albumGrid.albumModel === undefined
                || albumGrid.albumModel.length === 0
                || albumGrid.currentIndex < 0
                || albumGrid.currentIndex >= albumGrid.albumModel.length)
            return
        albumGrid.contextAlbum = albumGrid.albumModel[albumGrid.currentIndex]
        if (albumGrid.browseState && albumGrid.contextAlbum)
            albumGrid.browseState.remember(albumGrid.contextAlbum.key)
        albumContextMenu.popup()
    }

    function handleAlbumContextKey(event) {
        if (event.key === Qt.Key_Menu
                || (event.key === Qt.Key_F10
                    && (event.modifiers & Qt.ShiftModifier))) {
            albumGrid.openCurrentAlbumContext()
            event.accepted = true
            return true
        }
        return false
    }
    property real albumZoom: 1.0
    property var browseState: null
    property string spacingMode: "balanced"
    property string metadataLevel: "standard"
    property bool quickActions: true
    property bool precisionMetadata: false
    property bool layoutReady: false
    readonly property real contentMaxWidth: 1760
    readonly property real usableWidth: Math.min(width, contentMaxWidth)
    readonly property int minimumCardWidth: MichiThemeState.density === "compact"
        ? Math.round(154 * albumZoom)
        : MichiThemeState.density === "comfortable"
            ? Math.round(220 * albumZoom) : Math.round(184 * albumZoom)
    readonly property int maximumCardWidth: MichiThemeState.density === "compact"
        ? Math.round(184 * albumZoom)
        : MichiThemeState.density === "comfortable"
            ? Math.round(250 * albumZoom) : Math.round(216 * albumZoom)
    readonly property int cardGap: spacingMode === "tight" ? MichiSpacing.sm
        : spacingMode === "airy" ? MichiSpacing.xl : MichiThemeState.contentGap
    readonly property int columnCount: Math.max(1, Math.floor(
        (usableWidth + cardGap) / (minimumCardWidth + cardGap)))
    readonly property bool rowsFlowActive: flow === GridView.FlowLeftToRight
    readonly property real resolvedCardWidth: Math.min(maximumCardWidth,
        cellWidth - cardGap)
    readonly property int metadataHeight: metadataLevel === "minimal" ? 64
        : metadataLevel === "detailed" ? 112 : 86

    Layout.fillWidth: true
    Layout.fillHeight: true
    // A Loader may complete this component before its layout has assigned the
    // final width. Defer delegate creation one event-loop turn so GridView does
    // not retain cells positioned against the provisional one-column geometry.
    model: layoutReady ? albumModel : []
    flow: GridView.FlowLeftToRight
    leftMargin: Math.max(0, (width - usableWidth) / 2)
    rightMargin: leftMargin
    cellWidth: usableWidth / columnCount
    cellHeight: resolvedCardWidth + metadataHeight + cardGap
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    cacheBuffer: cellHeight * 2
    Accessible.role: Accessible.List
    Accessible.name: qsTr("Albums in grid view")
    Accessible.description: qsTr("Use arrow keys to browse and Enter to open an album")

    Component.onCompleted: {
        Qt.callLater(function() {
            layoutReady = true
            albumGrid.forceLayout()
            if (browseState) {
                var restoredIndex = browseState.galleryIndex
                if (browseState.currentKey) {
                    for (var i = 0; i < albumModel.length; ++i) {
                        if (albumModel[i].key === browseState.currentKey) {
                            restoredIndex = i
                            break
                        }
                    }
                }
                albumGrid.currentIndex = restoredIndex
                albumGrid.contentY = browseState.galleryContentY
            }
        })
    }
    onCellWidthChanged: if (layoutReady) albumGrid.forceLayout()
    onCellHeightChanged: if (layoutReady) albumGrid.forceLayout()
    onContentYChanged: if (browseState) browseState.galleryContentY = contentY
    onCurrentIndexChanged: if (browseState) {
        browseState.galleryIndex = currentIndex
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            browseState.remember(albumModel[currentIndex].key)
    }

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onPressed: function(event) {
        if (albumGrid.handleAlbumContextKey(event))
            return
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

    ScrollBar.vertical: MichiScrollBar { }

    delegate: Item {
        id: albumCell
        objectName: "albumGridCell"
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
            collectionFocus: albumGrid.activeFocus && albumCell.current
            metadataLevel: albumGrid.metadataLevel
            quickActionsVisible: albumGrid.quickActions
            precisionMetadata: albumGrid.precisionMetadata
            onActiveFocusChanged: {
                if (activeFocus)
                    albumGrid.currentIndex = albumCell.index
            }
            onSelectedRequested: {
                albumGrid.currentIndex = albumCell.index
            }
            onOpenRequested: {
                albumGrid.currentIndex = albumCell.index
                library.select_album(albumCell.modelData.key)
            }
            onPlayRequested: library.play_album(albumCell.modelData.key)
        }
    }

    // M9-R3 CONVERGENCE SEAL: menú raíz del teclado (roving del view).
    AlbumContextMenu {
        id: albumContextMenu
        album: albumGrid.contextAlbum
        z: 300
    }
}