import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

Item {
    id: searchOverlay
    property bool opened: false
    property int resultIndex: 0
    readonly property int visibleTrackCount: Math.min(6, library.searchTrackCount)
    readonly property int visibleAlbumCount: Math.min(6, library.searchAlbumCount)
    readonly property int visibleArtistCount: Math.min(6, library.searchArtistCount)
    readonly property int visiblePlaylistCount: Math.min(6, playlists.searchPlaylistCount)
    readonly property int visibleGenreCount: Math.min(6, library.searchGenreCount)
    // M9-R1J: M7 total + playlist local projection = the UI total. This is
    // PRESENTATION AGGREGATION — LibraryBridge total stays M7-only.
    readonly property int combinedResultCount:
        library.searchDisplayTotalCount + playlists.searchPlaylistCount
    readonly property int actionableResultCount: visibleTrackCount + visibleAlbumCount
        + visibleArtistCount + visiblePlaylistCount
        + visibleGenreCount
    signal closeRequested()
    signal navigationRequested(string routeId)
    // Qt 6 lazy bindings: `visible: opacity > 0` en el root dejaba el
    // subtree con bindings diferidos que nunca se re-evaluaban (el scroll
    // de resultados nunca renderizaba). Opacity alone + enabled controlan
    // la visibilidad sin romper la evaluación de los hijos.
    opacity: opened ? 1 : 0
    enabled: opened
    Keys.onEscapePressed: closeRequested()
    Behavior on opacity {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.panel; easing.type: MichiMotion.outCubic }
    }

    function moveResult(delta) {
        if (actionableResultCount <= 0)
            return
        resultIndex = (resultIndex + delta + actionableResultCount) % actionableResultCount
    }

    function activateResult() {
        if (resultIndex < visibleTrackCount) {
            library.activate(resultIndex)
            closeRequested()
            navigationRequested("now_playing")
            return
        }
        var albumIndex = resultIndex - visibleTrackCount
        if (albumIndex >= 0 && albumIndex < visibleAlbumCount) {
            library.select_album(library.albums[albumIndex].key)
            closeRequested()
            navigationRequested("library")
            return
        }
        var artistIndex = albumIndex - visibleAlbumCount
        if (artistIndex >= 0 && artistIndex < visibleArtistCount) {
            library.select_artist(library.artists[artistIndex].key)
            closeRequested()
            navigationRequested("library")
            return
        }
        var playlistIndex = artistIndex - visibleArtistCount
        if (playlistIndex >= 0 && playlistIndex < visiblePlaylistCount) {
            // M9-R1I: playlist results open the FIRST-CLASS PLAYLISTS route
            // (validated open intent) — never fall back to Library. Mouse
            // and keyboard activation converge to the same state.
            playlists.open_playlist(playlists.searchPlaylists[playlistIndex].playlistId)
            closeRequested()
            return
        }
        var genreIndex = playlistIndex - visiblePlaylistCount
        if (genreIndex >= 0 && genreIndex < visibleGenreCount) {
            library.select_genre(library.genres[genreIndex].key)
            closeRequested()
            navigationRequested("library")
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiSemanticColors.scrimStrong
        MouseArea { anchors.fill: parent; onClicked: searchOverlay.closeRequested() }
    }
    MichiGlassSurface {
        id: searchPanel
        objectName: "searchOverlayPanel"
        elevation: "modal"
        accented: true
        accentColor: MichiPalette.auroraCyan
        width: Math.min(720, searchOverlay.width - MichiSpacing.xxl * 2)
        height: Math.min(520, searchOverlay.height - MichiSpacing.xxl * 2)
        anchors.horizontalCenter: parent.horizontalCenter
        y: searchOverlay.opened ? MichiSpacing.xxxl : MichiSpacing.xxl
        Behavior on y {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.panel; easing.type: MichiMotion.outCubic }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: MichiSpacing.md
            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.md
                MichiSearchField {
                    id: searchInput
                    objectName: "searchOverlayInput"
                    Layout.fillWidth: true
                    text: library.searchQuery
                    placeholderText: qsTr("Search tracks, albums, artists and playlists")
                    onEdited: query => {
                        searchOverlay.resultIndex = 0
                        library.search(query)
                    }
                    onClearRequested: library.clear_search()
                    onNextResultRequested: searchOverlay.moveResult(1)
                    onPreviousResultRequested: searchOverlay.moveResult(-1)
                    onActivateResultRequested: searchOverlay.activateResult()
                    onEscapeRequested: searchOverlay.closeRequested()
                }
                MichiStatusChip {
                    text: qsTr("CTRL F")
                    dotVisible: false
                }
            }
            MichiStatusChip {
                visible: library.searchActive
                text: searchOverlay.combinedResultCount + " results · "
                    + library.searchTrackCount + " tracks · "
                    + library.searchAlbumCount + " albums · "
                    + library.searchArtistCount + " artists · "
                    + playlists.searchPlaylistCount + " playlists"
                tone: "active"
                Layout.alignment: Qt.AlignLeft
            }
            MichiDivider { Layout.fillWidth: true }
            EmptyState {
                objectName: "searchEmptyState"
                Layout.fillWidth: true; Layout.fillHeight: true
                visible: !library.searchActive || searchOverlay.combinedResultCount === 0
                title: library.searchActive ? "No results" : "Search your library"
                message: library.searchActive
                    ? "Try a title, artist, album, playlist, genre or composer."
                    : "Results are grouped by musical entity and remain fully local."
            }
            MichiScrollView {
                objectName: "searchResultsScroll"
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: library.searchActive && searchOverlay.combinedResultCount > 0
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.md

                    MichiText { text: "Tracks"; role: "section"; visible: library.searchTrackCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleTrackCount
                        delegate: TrackRow {
                            required property int index
                            Layout.fillWidth: true
                            title: library.songRows[index].title
                            trackId: library.songRows[index].trackId
                            filePath: library.songRows[index].path
                            artist: library.songRows[index].artist
                            artistKey: library.songRows[index].artistKey
                            album: library.songRows[index].album
                            albumKey: library.songRows[index].albumKey
                            durationMs: library.songRows[index].durationMs
                            formatKey: library.songRows[index].formatKey
                            formatLabel: library.songRows[index].formatLabel
                            codec: library.songRows[index].codec
                            container: library.songRows[index].container
                            dsdRate: library.songRows[index].dsdRate
                            sampleRateHz: library.songRows[index].sampleRateHz
                            bitDepth: library.songRows[index].bitDepth
                            bitrateBps: library.songRows[index].bitrateBps
                            channels: library.songRows[index].channels
                            fileSize: library.songRows[index].fileSize
                            genre: library.songRows[index].genre
                            composer: library.songRows[index].composer
                            year: library.songRows[index].year
                            artworkPath: library.songRows[index].artworkPath || ""
                            showArtwork: true
                            showFavorite: true
                            showAddToPlaylist: library.canAddTracksToPlaylists
                            showInspector: true
                            canQueue: library.canQueueTracks
                            canGoToAlbum: albumKey.length > 0
                            canGoToArtist: artistKey.length > 0
                            favorite: library.favoritePaths.indexOf(filePath) !== -1
                            playing: playback.currentPath === library.songRows[index].path
                            selected: searchOverlay.resultIndex === index
                            onActivated: {
                                library.activate_path(filePath)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("now_playing")
                            }
                            onFavoriteToggled: library.toggle_favorite(filePath)
                            onQueueRequested: library.queue_track(trackId)
                            onAddToPlaylistRequested:
                                library.request_tracks_playlist_target([trackId])
                            onInspectorRequested:
                                searchTrackProperties.inspect(library.songRows[index])
                            onSelectedRequested: searchOverlay.resultIndex = index
                            onGoToAlbumRequested: {
                                library.select_album(albumKey)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                            onGoToArtistRequested: {
                                library.select_artist(artistKey)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                        }
                    }

                    MichiText { text: "Albums"; role: "section"; visible: library.searchAlbumCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleAlbumCount
                        delegate: MichiEntityRow {
                            id: searchAlbumRow
                            required property int index
                            Layout.fillWidth: true
                            iconName: "album"
                            title: library.albums[index].title
                            subtitle: library.albums[index].artist
                            selected: searchOverlay.resultIndex === searchOverlay.visibleTrackCount + index
                            onActivated: {
                                library.select_album(library.albums[index].key)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                            Keys.onPressed: event => searchAlbumContext.handleContextKey(event)
                            AlbumContextArea {
                                id: searchAlbumContext
                                anchors.fill: parent
                                album: library.albums[index]
                                onContextRequested: searchOverlay.resultIndex
                                    = searchOverlay.visibleTrackCount + index
                            }
                        }
                    }

                    MichiText { text: "Artists"; role: "section"; visible: library.searchArtistCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleArtistCount
                        delegate: MichiEntityRow {
                            id: searchArtistRow
                            required property int index
                            Layout.fillWidth: true
                            iconName: "artist"
                            title: library.artists[index].name
                            technical: library.artists[index].trackCount + (library.artists[index].trackCount === 1 ? " track" : " tracks")
                            selected: searchOverlay.resultIndex === searchOverlay.visibleTrackCount
                                + searchOverlay.visibleAlbumCount + index
                            onActivated: {
                                library.select_artist(library.artists[index].key)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                            Keys.onPressed: event => searchArtistContext.handleContextKey(event)
                            ArtistContextArea {
                                id: searchArtistContext
                                anchors.fill: parent
                                artist: library.artists[index]
                                onContextRequested: searchOverlay.resultIndex
                                    = searchOverlay.visibleTrackCount
                                    + searchOverlay.visibleAlbumCount + index
                            }
                        }
                    }

                    MichiText { text: "Playlists"; role: "section"; visible: playlists.searchPlaylistCount > 0 }
                    Repeater {
                        id: playlistsRepeater
                        objectName: "playlistSearchRepeater"
                        model: searchOverlay.visiblePlaylistCount
                        delegate: MichiEntityRow {
                            objectName: "playlistSearchRow" + index
                            required property int index
                            Layout.fillWidth: true
                            iconName: "queue"
                            title: playlists.searchPlaylists[index].name
                            technical: playlists.searchPlaylists[index].trackCount + (playlists.searchPlaylists[index].trackCount === 1 ? " track" : " tracks")
                            selected: searchOverlay.resultIndex === searchOverlay.visibleTrackCount
                                + searchOverlay.visibleAlbumCount
                                + searchOverlay.visibleArtistCount + index
                            onActivated: {
                                // M9-R1: playlist result opens the first-class
                                // PLAYLISTS route (validated + Recent) — never
                                // Library > Playlists, never name resolution.
                                playlists.open_playlist(playlists.searchPlaylists[index].playlistId)
                                searchOverlay.closeRequested()
                            }
                        }
                    }

                    MichiText { text: "Genres"; role: "section"; visible: library.searchGenreCount > 0 }
                    Repeater {
                        model: Math.min(6, library.searchGenreCount)
                        delegate: MichiEntityRow {
                            id: searchGenreRow
                            required property int index
                            Layout.fillWidth: true
                            iconName: "genre"
                            title: library.genres[index].name
                            technical: library.genres[index].trackCount + (library.genres[index].trackCount === 1 ? " track" : " tracks")
                            selected: searchOverlay.resultIndex
                                === searchOverlay.visibleTrackCount
                                + searchOverlay.visibleAlbumCount
                                + searchOverlay.visibleArtistCount
                                + searchOverlay.visiblePlaylistCount + index
                            onActivated: {
                                library.select_genre(library.genres[index].key)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                            Keys.onPressed: event => searchGenreContext.handleContextKey(event)
                            GenreContextArea {
                                id: searchGenreContext
                                anchors.fill: parent
                                genre: library.genres[index]
                                onContextRequested: searchOverlay.resultIndex
                                    = searchOverlay.visibleTrackCount
                                    + searchOverlay.visibleAlbumCount
                                    + searchOverlay.visibleArtistCount
                                    + searchOverlay.visiblePlaylistCount + index
                            }
                        }
                    }
                }
            }
        }
        Component.onCompleted: if (searchOverlay.opened) searchInput.forceInputFocus()
    }
    onOpenedChanged: if (opened) {
        resultIndex = 0
        forceActiveFocus()
        searchInput.forceInputFocus()
    }
    TrackPropertiesView { id: searchTrackProperties }
}
