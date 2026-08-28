import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../theme"

Item {
    id: root

    property var rows: []
    property string playingPath: ""
    property var favoritePaths: []
    property bool showArtistColumn: true
    property bool showAlbumColumn: true
    property bool showArtwork: true
    property bool showActions: true
    property bool canFavorite: true
    property bool canQueue: true
    property bool canAddToPlaylist: true
    property bool canInspect: true
    property bool canNavigateEntities: true
    property bool sortingEnabled: false
    property string sortColumn: ""
    property bool sortDescending: false
    property string emptyTitle: qsTr("No tracks")
    property string emptyMessage: ""
    property string emptyIcon: "track"
    property int selectedIndex: -1
    property string numberingMode: "index"
    property bool selectionEnabled: false
    property var selectedTrackIds: []

    signal trackActivated(string path, int index)
    signal favoriteRequested(string path)
    signal queueRequested(string path)
    signal addToPlaylistRequested(string path)
    signal propertiesRequested(var track)
    signal goToAlbumRequested(string albumKey)
    signal goToArtistRequested(string artistKey)
    signal sortRequested(string column)
    signal selectionToggleRequested(string trackId)

    function numberText(row, index) {
        if (numberingMode === "disc-track") {
            var trackNumber = Number(row.trackNumber || 0)
            var discNumber = Number(row.discNumber || 0)
            if (discNumber > 1 && trackNumber > 0)
                return discNumber + "." + trackNumber
            if (trackNumber > 0)
                return String(trackNumber)
        }
        return String(index + 1)
    }

    readonly property real horizontalPadding: MichiSpacing.sm * 2
    readonly property int visibleColumnCount: 1
        + (showArtwork && LibraryTrackColumnState.artworkVisible ? 1 : 0)
        + (LibraryTrackColumnState.titleVisible ? 1 : 0)
        + (showArtistColumn && LibraryTrackColumnState.artistVisible ? 1 : 0)
        + (showAlbumColumn && LibraryTrackColumnState.albumVisible ? 1 : 0)
        + (LibraryTrackColumnState.formatVisible ? 1 : 0)
        + (LibraryTrackColumnState.sampleRateVisible ? 1 : 0)
        + (LibraryTrackColumnState.bitDepthVisible ? 1 : 0)
        + (LibraryTrackColumnState.dsdRateVisible ? 1 : 0)
        + (LibraryTrackColumnState.bitrateVisible ? 1 : 0)
        + (LibraryTrackColumnState.channelsVisible ? 1 : 0)
        + (LibraryTrackColumnState.fileSizeVisible ? 1 : 0)
        + (LibraryTrackColumnState.genreVisible ? 1 : 0)
        + (LibraryTrackColumnState.composerVisible ? 1 : 0)
        + (LibraryTrackColumnState.yearVisible ? 1 : 0)
        + (LibraryTrackColumnState.durationVisible ? 1 : 0)
        + (showActions && LibraryTrackColumnState.actionsVisible ? 1 : 0)
    readonly property real nonTitleWidth: LibraryTrackColumnState.numberWidth
        + (showArtwork && LibraryTrackColumnState.artworkVisible ? LibraryTrackColumnState.artworkWidth : 0)
        + (showArtistColumn && LibraryTrackColumnState.artistVisible ? LibraryTrackColumnState.artistWidth : 0)
        + (showAlbumColumn && LibraryTrackColumnState.albumVisible ? LibraryTrackColumnState.albumWidth : 0)
        + (LibraryTrackColumnState.formatVisible ? LibraryTrackColumnState.formatWidth : 0)
        + (LibraryTrackColumnState.sampleRateVisible ? LibraryTrackColumnState.sampleRateWidth : 0)
        + (LibraryTrackColumnState.bitDepthVisible ? LibraryTrackColumnState.bitDepthWidth : 0)
        + (LibraryTrackColumnState.dsdRateVisible ? LibraryTrackColumnState.dsdRateWidth : 0)
        + (LibraryTrackColumnState.bitrateVisible ? LibraryTrackColumnState.bitrateWidth : 0)
        + (LibraryTrackColumnState.channelsVisible ? LibraryTrackColumnState.channelsWidth : 0)
        + (LibraryTrackColumnState.fileSizeVisible ? LibraryTrackColumnState.fileSizeWidth : 0)
        + (LibraryTrackColumnState.genreVisible ? LibraryTrackColumnState.genreWidth : 0)
        + (LibraryTrackColumnState.composerVisible ? LibraryTrackColumnState.composerWidth : 0)
        + (LibraryTrackColumnState.yearVisible ? LibraryTrackColumnState.yearWidth : 0)
        + (LibraryTrackColumnState.durationVisible ? LibraryTrackColumnState.durationWidth : 0)
        + (showActions && LibraryTrackColumnState.actionsVisible ? LibraryTrackColumnState.actionsWidth : 0)
    readonly property real gapsWidth: Math.max(0, visibleColumnCount - 1) * MichiSpacing.md
    readonly property real titleColumnWidth: LibraryTrackColumnState.titleVisible
        ? Math.max(LibraryTrackColumnState.titleWidth,
            width - horizontalPadding - nonTitleWidth - gapsWidth) : 0
    readonly property real tableContentWidth: horizontalPadding + nonTitleWidth
        + titleColumnWidth + gapsWidth

    ListView {
        id: trackList
        objectName: "michiTrackTable"
        anchors.fill: parent
        model: root.rows
        clip: true
        spacing: MichiSpacing.xs
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationEnabled: true
        keyNavigationWraps: false
        activeFocusOnTab: true
        reuseItems: true
        cacheBuffer: height
        contentWidth: Math.max(width, root.tableContentWidth)
        headerPositioning: ListView.OverlayHeader
        Accessible.role: Accessible.Table
        Accessible.name: qsTr("Tracks")
        ScrollBar.vertical: MichiScrollBar { }
        ScrollBar.horizontal: MichiScrollBar { }

        header: ResizableTrackHeader {
            width: Math.max(trackList.width, root.tableContentWidth)
            titleColumnWidth: root.titleColumnWidth
            showArtistColumn: root.showArtistColumn
            showAlbumColumn: root.showAlbumColumn
            showArtwork: root.showArtwork
            showActions: root.showActions
            sortingEnabled: root.sortingEnabled
            sortColumn: root.sortColumn
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
        }

        delegate: TrackRow {
            required property int index
            required property var modelData
            width: Math.max(trackList.width, root.tableContentWidth)
            titleColumnWidth: root.titleColumnWidth
            sharedGeometry: true
            showTechnicalColumns: true
            showActions: root.showActions
            numberText: root.numberText(modelData, index)
            trackId: modelData.trackId || modelData.path
            filePath: modelData.path
            title: modelData.title || modelData.displayName
            artist: modelData.artist || ""
            artistKey: modelData.artistKey || ""
            album: modelData.album || ""
            albumKey: modelData.albumKey || ""
            durationMs: modelData.durationMs || 0
            artworkPath: modelData.artworkPath || ""
            formatKey: modelData.formatKey || "unknown"
            formatLabel: modelData.formatLabel || "UNKNOWN"
            codec: modelData.codec || ""
            container: modelData.container || ""
            dsdRate: modelData.dsdRate || ""
            sampleRateHz: modelData.sampleRateHz || 0
            bitDepth: modelData.bitDepth || 0
            bitrateBps: modelData.bitrateBps || 0
            channels: modelData.channels || 0
            fileSize: modelData.fileSize || 0
            genre: modelData.genre || ""
            composer: modelData.composer || ""
            year: modelData.year || 0
            showArtistColumn: root.showArtistColumn
            showAlbumColumn: root.showAlbumColumn
            showArtwork: root.showArtwork
            playing: root.playingPath === modelData.path
            selected: root.selectionEnabled
                ? root.selectedTrackIds.indexOf(modelData.trackId) !== -1
                : root.selectedIndex === index
            favorite: root.favoritePaths.indexOf(modelData.path) !== -1
            showFavorite: root.canFavorite
            showAddToPlaylist: root.canAddToPlaylist
            showInspector: root.canInspect
            canQueue: root.canQueue
            canGoToAlbum: root.canNavigateEntities && albumKey.length > 0
            canGoToArtist: root.canNavigateEntities && artistKey.length > 0
            onSelectedRequested: {
                root.selectedIndex = index
                trackList.currentIndex = index
            }
            onActivated: {
                if (root.selectionEnabled)
                    root.selectionToggleRequested(modelData.trackId)
                else
                    root.trackActivated(modelData.path, index)
            }
            onFavoriteToggled: root.favoriteRequested(modelData.path)
            onQueueRequested: root.queueRequested(modelData.path)
            onAddToPlaylistRequested: root.addToPlaylistRequested(modelData.path)
            onInspectorRequested: root.propertiesRequested(modelData)
            onGoToAlbumRequested: root.goToAlbumRequested(modelData.albumKey)
            onGoToArtistRequested: root.goToArtistRequested(modelData.artistKey)
        }
    }

    EmptyState {
        anchors.fill: parent
        visible: root.rows.length === 0
        title: root.emptyTitle
        message: root.emptyMessage
        iconName: root.emptyIcon
    }
}
