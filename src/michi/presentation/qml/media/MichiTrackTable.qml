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
    property var favoriteTrackIds: []
    property var favoritePaths: []
    property bool showArtistColumn: true
    property bool showAlbumColumn: true
    property bool showArtwork: true
    property bool showActions: true
    property string columnProfile: "songs"
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
    readonly property bool profileShowsArtwork: showArtwork
        && columnProfile !== "album"
    readonly property bool profileShowsArtist: showArtistColumn
        && columnProfile !== "artist"
    readonly property bool profileShowsAlbum: showAlbumColumn
        && columnProfile !== "album"

    // CORRECTIVE SEAL §11: identity-sensitive intents carry the STABLE
    // TrackId (path stays as the factual location projection).
    signal trackActivated(string trackId, string path, int index)
    signal favoriteRequested(string trackId)
    signal queueRequested(string trackId)
    // PR #231 REVIEW SEAL (P1-01): the playlist seam is a HISTORICALLY
    // path-based API — carry the factual path next to the TrackId so the
    // durable playlist entry is the audio file location, never the UUID.
    // TrackId remains the identity authority for activation/favorite/queue.
    signal addToPlaylistRequested(string trackId, string path)
    signal propertiesRequested(var track)
    signal goToAlbumRequested(string albumKey)
    signal goToArtistRequested(string artistKey)
    signal sortRequested(string column)
    // LIB-A §15: dirección EXPLÍCITA (el menú contextual nunca simula
    // Sort Descending con dos toggles).
    signal sortDirectionRequested(string column, bool descending)
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
        + (profileShowsArtwork && LibraryTrackColumnState.artworkVisible ? 1 : 0)
        + (LibraryTrackColumnState.titleVisible ? 1 : 0)
        + (profileShowsArtist && LibraryTrackColumnState.artistVisible ? 1 : 0)
        + (profileShowsAlbum && LibraryTrackColumnState.albumVisible ? 1 : 0)
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
        + (profileShowsArtwork && LibraryTrackColumnState.artworkVisible ? LibraryTrackColumnState.artworkWidth : 0)
        + (profileShowsArtist && LibraryTrackColumnState.artistVisible ? LibraryTrackColumnState.artistWidth : 0)
        + (profileShowsAlbum && LibraryTrackColumnState.albumVisible ? LibraryTrackColumnState.albumWidth : 0)
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
        ? LibraryTrackColumnState.titleWidth : 0
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
        cacheBuffer: Math.max(0, height)
        contentWidth: Math.max(width, root.tableContentWidth)
        headerPositioning: ListView.OverlayHeader
        Accessible.role: Accessible.Table
        Accessible.name: qsTr("Tracks")
        ScrollBar.vertical: MichiScrollBar { }
        ScrollBar.horizontal: MichiScrollBar { }

        header: ResizableTrackHeader {
            width: Math.max(trackList.width, root.tableContentWidth)
            titleColumnWidth: root.titleColumnWidth
            showArtistColumn: root.profileShowsArtist
            showAlbumColumn: root.profileShowsAlbum
            showArtwork: root.profileShowsArtwork
            showActions: root.showActions
            sortingEnabled: root.sortingEnabled
            sortColumn: root.sortColumn
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onSortDirectionRequested: (column, descending) =>
                root.sortDirectionRequested(column, descending)
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
            trackId: modelData.trackId
                && String(modelData.trackId).length > 0
                ? String(modelData.trackId)
                : "legacy-path::" + String(modelData.path)
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
            showArtistColumn: root.profileShowsArtist
            showAlbumColumn: root.profileShowsAlbum
            showArtwork: root.profileShowsArtwork
            // P1-LIB-05: ONE boolean fact from the domain predicate —
            // TrackRow blocks activation and dims; no string compares.
            unavailable: Boolean(modelData.unavailable)
            playing: root.playingPath === modelData.path
            selected: root.selectionEnabled
                ? root.selectedTrackIds.indexOf(trackId) !== -1
                : root.selectedIndex === index
            favorite:
                // LIB-A §7/24: triple check canónico — id estable, proyección
                // legacy (legacy-path::<path>) y path-only (pre-migración).
                root.favoriteTrackIds.indexOf(trackId) !== -1
                || (modelData.path
                    && root.favoriteTrackIds.indexOf(
                        "legacy-path::" + modelData.path) !== -1)
                || ((!modelData.trackId
                     || String(modelData.trackId).length === 0)
                    && root.favoritePaths.indexOf(modelData.path) !== -1)
            showFavorite: root.canFavorite
            showAddToPlaylist: root.canAddToPlaylist
            showInspector: root.canInspect
            // LIB-A §6: unavailable → queue NO (la availability por fila
            // no se pierde aunque el host permita queue).
            canQueue: root.canQueue && !Boolean(modelData.unavailable)
            canGoToAlbum: root.canNavigateEntities && albumKey.length > 0
            canGoToArtist: root.canNavigateEntities && artistKey.length > 0
            onSelectedRequested: {
                root.selectedIndex = index
                trackList.currentIndex = index
            }
            onActivated: {
                if (root.selectionEnabled)
                    root.selectionToggleRequested(trackId)
                else
                    root.trackActivated(trackId, modelData.path, index)
            }
            onFavoriteToggled: root.favoriteRequested(trackId)
            onQueueRequested: root.queueRequested(trackId)
            onAddToPlaylistRequested: root.addToPlaylistRequested(
                trackId, modelData.path)
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
