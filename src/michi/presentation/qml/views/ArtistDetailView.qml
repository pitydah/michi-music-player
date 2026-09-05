import QtQuick
import QtQuick.Layouts
import "../controls"
import "../enrichment"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    objectName: "artistDetailView"
    property string addTargetPath: ""

    spacing: MichiThemeState.contentGap
    visible: library.selectedArtistKey !== ""

    /* M6.9: activation is explicit — the artist detail drives enrichment
     * for the selected artist. Lists/search/scan never trigger it. */
    readonly property string selectedArtistKey: library.selectedArtistKey
    onSelectedArtistKeyChanged: {
        if (root.selectedArtistKey.length > 0)
            enrichment.activate_artist(root.selectedArtistKey)
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.lg

        Rectangle {
            Layout.preferredWidth: 92
            Layout.preferredHeight: 92
            radius: 46
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: MichiPalette.auroraBlue }
                GradientStop { position: 0.5; color: MichiPalette.auroraCyan }
                GradientStop { position: 1; color: MichiPalette.auroraPurple }
            }
            Artwork {
                anchors.fill: parent
                anchors.margins: 3
                radius: width / 2
                requestedSize: 192
                /* M6.9: external artist portrait wins when present;
                 * local representative artwork is the fallback. */
                sourcePath: enrichment.artistArtworkPath.length > 0
                    ? enrichment.artistArtworkPath
                    : (library.artistAlbums.length > 0
                        ? library.artistAlbums[0].artworkPath : "")
                fallbackText: library.artistName
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiButton {
                text: "Back"
                variant: "ghost"
                Layout.alignment: Qt.AlignLeft
                onClicked: library.clear_artist_selection()
            }
            MichiText {
                Layout.fillWidth: true
                text: library.artistName
                role: "display"
                elide: Text.ElideRight
            }
            MichiText {
                text: library.artistAlbumCount + " albums · "
                    + library.artistTrackCount + " tracks"
                role: "secondary"
            }
        }
    }

    /* M6.9 — online knowledge surface (between hero and Albums) */
    EnrichmentStatusBar {
        Layout.fillWidth: true
        state: enrichment.state
        message: enrichment.stateMessage
        busy: enrichment.busy
        visible: enrichment.activeKind === "artist"
    }

    EnrichmentKnowledgeCard {
        Layout.fillWidth: true
        title: "About the artist"
        knowledge: enrichment.artistKnowledge
        hasKnowledge: enrichment.artistHasKnowledge
        sources: enrichment.artistAttributions
        visible: enrichment.activeKind === "artist"
    }

    EnrichmentActions {
        Layout.fillWidth: true
        kind: "artist"
        state: enrichment.state
        onlineEnabled: enrichment.onlineEnabled
        hasKnowledge: enrichment.artistHasKnowledge
        visible: enrichment.activeKind === "artist"
        onRefreshRequested: enrichment.refresh_artist()
        onReviewRequested: enrichment.open_review("artist")
        onClearRequested: enrichment.clear_knowledge()
        onResetRequested: enrichment.reset_identity()
    }

    MichiText {
        text: qsTr("Albums")
        role: "section"
        visible: library.artistAlbums.length > 0
    }

    GridView {
        id: artistAlbumsGrid
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? Math.min(220, contentHeight) : 0
        visible: library.artistAlbums.length > 0
        model: library.artistAlbums
        cellWidth: 176
        cellHeight: 214
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        delegate: AlbumCard {
            required property var modelData
            width: artistAlbumsGrid.cellWidth - MichiSpacing.sm
            album: modelData
            onOpenRequested: library.select_album(modelData.key)
            onPlayRequested: library.play_album(modelData.key)
        }
    }

    MichiText { text: qsTr("Tracks"); role: "section" }

    MichiTrackTable {
        id: artistTracksTable
        objectName: "artistTracksTable"
        Layout.fillWidth: true
        Layout.fillHeight: true
        rows: library.artistTracks
        playingPath: typeof playback !== "undefined" && playback ? playback.currentPath : ""
        favoriteTrackIds: library.favoriteTrackIds
        favoritePaths: library.favoritePaths
        // LIB-A §8/23: perfil de artista (artista implícito) + Go to Album.
        columnProfile: "artist"
        numberingMode: "index"
        showArtistColumn: false
        showAlbumColumn: true
        canFavorite: true
        canQueue: library.canQueueTracks
        canNavigateEntities: true
        canInspect: false
        // TrackId-first (el Bridge resuelve legacy-path::).
        onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
        onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
        onQueueRequested: trackId => library.queue_track_by_id(trackId)
        onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    }

    /* M6.9 — manual review dialog */
    ReviewMatchesDialog {
        id: reviewDialog
        visible: enrichment.reviewOpen && enrichment.reviewKind === "artist"
        kind: "artist"
        loading: enrichment.reviewLoading
        errorText: enrichment.reviewError
        artistCandidates: enrichment.artistCandidates
        onlineEnabled: enrichment.onlineEnabled
        onSearchRequested: function (name) { enrichment.search_artist(name) }
        onConfirmArtist: function (id) { enrichment.confirm_artist_candidate(id) }
        onClosed: enrichment.close_review()
    }
}
