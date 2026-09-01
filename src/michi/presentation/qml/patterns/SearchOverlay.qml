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
    // M9-R1J: M7 total + playlist local projection = the UI total. This is
    // PRESENTATION AGGREGATION — LibraryBridge total stays M7-only.
    readonly property int combinedResultCount:
        library.searchDisplayTotalCount + playlists.searchPlaylistCount
    readonly property int actionableResultCount: visibleTrackCount + visibleAlbumCount
        + visibleArtistCount + visiblePlaylistCount
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
                            artist: library.songRows[index].artist
                            album: library.songRows[index].album
                            durationMs: library.songRows[index].durationMs
                            quality: library.songRows[index].qualityLabel
                            artworkPath: library.songRows[index].artworkPath || ""
                            showArtwork: true
                            playing: playback.currentPath === library.songRows[index].path
                            selected: searchOverlay.resultIndex === index
                            onActivated: {
                                library.activate(index)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("now_playing")
                            }
                        }
                    }

                    MichiText { text: "Albums"; role: "section"; visible: library.searchAlbumCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleAlbumCount
                        delegate: MichiButton {
                            required property int index
                            Layout.fillWidth: true
                            text: library.albums[index].title + " · " + library.albums[index].artist
                            variant: "ghost"
                            selected: searchOverlay.resultIndex === searchOverlay.visibleTrackCount + index
                            onClicked: {
                                library.select_album(library.albums[index].key)
                                searchOverlay.closeRequested()
                                searchOverlay.navigationRequested("library")
                            }
                        }
                    }

                    MichiText { text: "Artists"; role: "section"; visible: library.searchArtistCount > 0 }
                    Repeater {
                        model: searchOverlay.visibleArtistCount
                        delegate: MichiEntityRow {
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
                            required property int index
                            Layout.fillWidth: true
                            iconName: "genre"
                            title: library.genres[index].name
                            technical: library.genres[index].trackCount + (library.genres[index].trackCount === 1 ? " track" : " tracks")
                            interactive: false
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
