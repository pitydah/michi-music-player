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
    readonly property int visibleGenreCount: Math.min(6, library.searchGenreCount)
    readonly property int visiblePlaylistCount: Math.min(6, playlists.searchPlaylistCount)
    // POST-R4 P1: UNA autoridad de offsets del resultado canónico
    // (Tracks → Albums → Artists → Playlists → Genres). Render,
    // selección y activación consumen ESTAS propiedades encadenadas —
    // nunca sumas manuales por grupo (el genre omitiendo
    // visiblePlaylistCount seleccionaba playlist y genre a la vez).
    readonly property int trackStart: 0
    readonly property int albumStart: trackStart + visibleTrackCount
    readonly property int artistStart: albumStart + visibleAlbumCount
    readonly property int playlistStart: artistStart + visibleArtistCount
    readonly property int genreStart: playlistStart + visiblePlaylistCount
    readonly property int resultEnd: genreStart + visibleGenreCount
    // M9-R1J: M7 total + playlist local projection = the UI total. This is
    // PRESENTATION AGGREGATION — LibraryBridge total stays M7-only.
    readonly property int combinedResultCount:
        library.searchDisplayTotalCount + playlists.searchPlaylistCount
    readonly property int actionableResultCount: resultEnd
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

    // R5: el overlay expone el row de Properties al host compartido vía
    // la señal del bridge (album_properties no aplica): el row se abre en
    // la TrackPropertiesView del host usando la señal del overlay.
    signal trackInspectionRequested(var trackRow)

    function inspectTrack(trackRow) {
        searchOverlay.trackInspectionRequested(trackRow)
    }

    function _favoriteAt(index) {
        var trackId = library.songRows[index].trackId
        if (!trackId || String(trackId).length === 0)
            return library.favoritePaths.indexOf(library.songRows[index].path) !== -1
        return library.favoriteTrackIds.indexOf(trackId) !== -1
    }

    function _favoritesChanged() {
        // El bridge notifica library_changed: no se necesita nada local.
    }

    function resultKindAt(globalIndex) {
        if (globalIndex < trackStart || globalIndex >= resultEnd)
            return ""
        if (globalIndex < albumStart)
            return "track"
        if (globalIndex < artistStart)
            return "album"
        if (globalIndex < playlistStart)
            return "artist"
        if (globalIndex < genreStart)
            return "playlist"
        return "genre"
    }

    function localIndexFor(globalIndex, start) {
        return globalIndex - start
    }

    // POST-R4 P1: seam ÚNICO de activación de track — TrackId es la
    // identidad (el índice visual jamás activa). Para registros legacy
    // sin TrackId el contrato aprobado del bridge activa por PATH
    // resuelto (activate_path → resolve_trackref): nunca el índice.
    function activateTrack(row) {
        var trackId = row && row.trackId ? String(row.trackId) : ""
        if (trackId.length > 0) {
            library.activate_track_by_id(trackId)
        } else {
            library.activate_path(row ? String(row.path) : "")
        }
        searchOverlay.closeRequested()
        searchOverlay.navigationRequested("now_playing")
    }

    function activateResult() {
        var kind = resultKindAt(resultIndex)
        if (kind === "")
            return
        if (kind === "track") {
            searchOverlay.activateTrack(
                library.songRows[localIndexFor(resultIndex, trackStart)]
            )
            return
        }
        if (kind === "album") {
            var albumLocal = localIndexFor(resultIndex, albumStart)
            library.select_album(library.albums[albumLocal].key)
            closeRequested()
            navigationRequested("library")
            return
        }
        if (kind === "artist") {
            var artistLocal = localIndexFor(resultIndex, artistStart)
            library.select_artist(library.artists[artistLocal].key)
            closeRequested()
            navigationRequested("library")
            return
        }
        if (kind === "playlist") {
            // M9-R1I: playlist results open the FIRST-CLASS PLAYLISTS route
            // (validated open intent) — never fall back to Library. Mouse
            // and keyboard activation converge to the same state.
            var playlistLocal = localIndexFor(resultIndex, playlistStart)
            playlists.open_playlist(
                playlists.searchPlaylists[playlistLocal].playlistId
            )
            closeRequested()
            return
        }
        // R5: género → filtro exact-key de Library (Songs tab).
        var genreLocal = localIndexFor(resultIndex, genreStart)
        library.select_genre(library.genres[genreLocal].key)
        closeRequested()
        navigationRequested("library")
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
                text: qsTr("%n result(s)", "", searchOverlay.combinedResultCount)
                    + " · " + qsTr("%n track(s)", "", library.searchTrackCount)
                    + " · " + qsTr("%n album(s)", "", library.searchAlbumCount)
                    + " · " + qsTr("%n artist(s)", "", library.searchArtistCount)
                    + " · " + qsTr("%n playlist(s)", "", playlists.searchPlaylistCount)
                tone: "active"
                Layout.alignment: Qt.AlignLeft
            }
            MichiDivider { Layout.fillWidth: true }
            EmptyState {
                objectName: "searchEmptyState"
                Layout.fillWidth: true; Layout.fillHeight: true
                visible: !library.searchActive || searchOverlay.combinedResultCount === 0
                title: library.searchActive ? qsTr("No results") : qsTr("Search your library")
                message: library.searchActive
                    ? qsTr("Try a title, artist, album, playlist, genre or composer.")
                    : qsTr("Results are grouped by musical entity and remain fully local.")
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

                    MichiText { text: qsTr("Tracks"); role: "section"; visible: library.searchTrackCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleTrackCount
                        delegate: TrackRow {
                            required property int index
                            Layout.fillWidth: true
                            trackId: library.songRows[index].trackId
                            title: library.songRows[index].title
                            artist: library.songRows[index].artist
                            album: library.songRows[index].album
                            albumKey: library.songRows[index].albumKey || ""
                            artistKey: library.songRows[index].artistKey || ""
                            durationMs: library.songRows[index].durationMs
                            quality: library.songRows[index].qualityLabel
                            artworkPath: library.songRows[index].artworkPath || ""
                            showArtwork: true
                            playing: playback.currentPath === library.songRows[index].path
                            selected: searchOverlay.resultIndex
                                === searchOverlay.trackStart + index
                            // R5 (§14): contexto de track completo — las
                            // acciones de la fila y del menú usan la
                            // identidad estable (TrackId), nunca el índice.
                            showFavorite: true
                            favorite: searchOverlay._favoriteAt(index)
                            canQueue: library.canQueueTracks
                            showAddToPlaylist: library.canAddTracksToPlaylists
                            showAddToNewPlaylist: true
                            showInspector: true
                            unavailable: Boolean(library.songRows[index].unavailable)
                            // POST-R4 P1: el mouse recorre el MISMO seam de
                            // activación que el teclado (TrackId, nunca
                            // índice).
                            onActivated: searchOverlay.activateTrack(
                                library.songRows[index]
                            )
                            onFavoriteToggled: {
                                library.toggle_favorite_by_id(library.songRows[index].trackId)
                                searchOverlay._favoritesChanged()
                            }
                            onQueueRequested: library.queue_track_by_id(library.songRows[index].trackId)
                            onAddToPlaylistRequested: library.request_tracks_playlist_target([library.songRows[index].trackId])
                            onInspectorRequested: searchOverlay.inspectTrack(library.songRows[index])
                            onGoToAlbumRequested: {
                                library.select_album(library.songRows[index].albumKey)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                            onGoToArtistRequested: {
                                library.select_artist(library.songRows[index].artistKey)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                        }
                    }

                    MichiText { text: qsTr("Albums"); role: "section"; visible: library.searchAlbumCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleAlbumCount
                        delegate: Item {
                            required property int index
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            MichiButton {
                                anchors.fill: parent
                                text: library.albums[index].title + " · " + library.albums[index].artist
                                variant: "ghost"
                                selected: searchOverlay.resultIndex
                                    === searchOverlay.albumStart + index
                                onClicked: {
                                    library.select_album(library.albums[index].key)
                                    searchOverlay.closeRequested()
                                    searchOverlay.navigationRequested("library")
                                }
                            }
                            // R5 (§15): el resultado del álbum es una ENTIDAD
                            // contextual — right-click/Menu/Shift+F10 abren
                            // el menú del álbum (Open/Play/Queue/Add/Create/
                            // Go Artist/Properties) con la key exacta.
                            AlbumContextArea {
                                anchors.fill: parent
                                album: library.albums[index]
                                canAddToPlaylist: true
                                canCreatePlaylist: true
                                canShowProperties: true
                                onContextRequested: {
                                    // selección exacta del resultado.
                                    searchOverlay.resultIndex = searchOverlay.albumStart + index
                                }
                            }
                        }
                    }

                    MichiText { text: qsTr("Artists"); role: "section"; visible: library.searchArtistCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleArtistCount
                        delegate: Item {
                            required property int index
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            MichiEntityRow {
                                anchors.fill: parent
                                iconName: "artist"
                                title: library.artists[index].name
                                technical: qsTr("%n track(s)", "",
                                    library.artists[index].trackCount)
                                selected: searchOverlay.resultIndex
                                    === searchOverlay.artistStart + index
                                onActivated: {
                                    library.select_artist(library.artists[index].key)
                                    searchOverlay.closeRequested()
                                    searchOverlay.navigationRequested("library")
                                }
                            }
                            // R5 (§15): el artista es una entidad contextual —
                            // Open/Queue/Add/Create vía el menú exacto.
                            ArtistContextArea {
                                anchors.fill: parent
                                artist: library.artists[index]
                                canAddToPlaylist: true
                                canCreatePlaylist: true
                                onContextRequested: {
                                    searchOverlay.resultIndex
                                        = searchOverlay.artistStart + index
                                }
                            }
                        }
                    }

                    MichiText { text: qsTr("Playlists"); role: "section"; visible: playlists.searchPlaylistCount > 0 }
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
                            technical: qsTr("%n track(s)", "",
                                playlists.searchPlaylists[index].trackCount)
                            selected: searchOverlay.resultIndex
                                === searchOverlay.playlistStart + index
                            onActivated: {
                                // M9-R1: playlist result opens the first-class
                                // PLAYLISTS route (validated + Recent) — never
                                // Library > Playlists, never name resolution.
                                playlists.open_playlist(playlists.searchPlaylists[index].playlistId)
                                searchOverlay.closeRequested()
                            }
                        }
                    }

                    MichiText { text: qsTr("Genres"); role: "section"; visible: library.searchGenreCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleGenreCount
                        delegate: MichiEntityRow {
                            required property int index
                            Layout.fillWidth: true
                            iconName: "genre"
                            title: library.genres[index].name
                            technical: qsTr("%n track(s)", "",
                                library.genres[index].trackCount)
                            // R5: el género es accionable con su EXACT KEY
                            // (select_genre) — el filtro de Library se aplica
                            // con la entidad exacta, nunca con el nombre.
                            interactive: true
                            selected: searchOverlay.resultIndex
                                === searchOverlay.genreStart + index
                            onActivated: {
                                library.select_genre(library.genres[index].key)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
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
}
