import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../enrichment"
import "../media"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    objectName: "artistDetailView"
    signal addToPlaylistRequested(string path)
    readonly property string selectedArtistKey: library.selectedArtistKey
    readonly property real minimumTracksHeight: MichiMetrics.controlLarge * 5
    readonly property real minimumSummaryViewportHeight: MichiMetrics.controlLarge * 3
    readonly property real summaryHeightBudget: Math.max(
        minimumSummaryViewportHeight,
        height - backButton.implicitHeight - tracksHeading.implicitHeight
            - minimumTracksHeight - spacing * 3)

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap
    visible: library.selectedArtistKey !== ""

    onSelectedArtistKeyChanged: {
        if (root.selectedArtistKey.length > 0)
            enrichment.activate_artist(root.selectedArtistKey)
    }

    MichiButton {
        id: backButton
        text: qsTr("Artists")
        iconName: "back"
        variant: "ghost"
        Layout.alignment: Qt.AlignLeft
        accessibleName: qsTr("Back to Artists")
        onClicked: library.clear_artist_selection()
    }

    Flickable {
        id: summaryFlick
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(
            summaryColumn.implicitHeight, root.summaryHeightBudget)
        contentWidth: width
        contentHeight: summaryColumn.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: MichiScrollBar { }

        Column {
            id: summaryColumn
            width: summaryFlick.width
            spacing: MichiThemeState.contentGap

            RowLayout {
                width: parent.width
                spacing: MichiSpacing.xl

                ArtistPortraitArtwork {
                    Layout.preferredWidth: 128
                    Layout.preferredHeight: 128
                    sourcePath: enrichment.artistArtworkPath.length > 0
                        ? enrichment.artistArtworkPath
                        : (library.artistAlbums.length > 0
                            ? library.artistAlbums[0].artworkPath : "")
                    fallbackText: library.artistName
                    requestedSize: 256
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: MichiSpacing.sm
                    MichiText {
                        Layout.fillWidth: true
                        text: library.artistName
                        role: "display"
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    MichiText {
                        text: library.artistAlbumCount
                            + (library.artistAlbumCount === 1
                                ? qsTr(" album") : qsTr(" albums"))
                            + " · " + library.artistTrackCount
                            + (library.artistTrackCount === 1
                                ? qsTr(" track") : qsTr(" tracks"))
                        role: "secondary"
                        color: MichiPalette.textSecondary
                    }
                }
            }

            EnrichmentInlineState {
                width: parent.width
                kind: "artist"
                state: enrichment.state
                message: enrichment.stateMessage
                busy: enrichment.busy
                onlineEnabled: enrichment.onlineEnabled
                hasKnowledge: enrichment.artistHasKnowledge
                active: enrichment.activeKind === "artist"
                onRefreshRequested: enrichment.refresh_artist()
                onReviewRequested: enrichment.open_review("artist")
                onClearRequested: enrichment.clear_knowledge()
                onResetRequested: enrichment.reset_identity()
            }

            EnrichmentKnowledgeCard {
                width: parent.width
                title: qsTr("About the artist")
                knowledge: enrichment.artistKnowledge
                hasKnowledge: enrichment.artistHasKnowledge
                sources: enrichment.artistAttributions
                visible: enrichment.activeKind === "artist" && enrichment.artistHasKnowledge
            }

            MichiText {
                text: qsTr("Albums")
                role: "section"
                visible: library.artistAlbums.length > 0
            }

            ListView {
                id: artistAlbumsGrid
                readonly property real albumCardWidth: 166
                readonly property real albumCardHeight: 236
                width: parent.width
                implicitHeight: visible && count > 0
                    ? albumCardHeight + (albumScrollBar.visible
                        ? albumScrollBar.implicitHeight : 0)
                    : 0
                height: implicitHeight
                visible: library.artistAlbums.length > 0
                model: library.artistAlbums
                orientation: ListView.Horizontal
                spacing: MichiSpacing.sm
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.horizontal: MichiScrollBar { id: albumScrollBar }
                Accessible.role: Accessible.List
                Accessible.name: qsTr("Albums by this artist")
                delegate: AlbumCard {
                    required property var modelData
                    width: artistAlbumsGrid.albumCardWidth
                    height: artistAlbumsGrid.albumCardHeight
                    album: modelData
                    onActivated: library.select_album(modelData.key)
                }
            }
        }
    }

    MichiText {
        id: tracksHeading
        text: qsTr("Tracks")
        role: "section"
    }

    MichiTrackTable {
        id: artistTracksTable
        Layout.fillWidth: true
        Layout.fillHeight: true
        rows: library.artistTracks
        playingPath: playback.currentPath
        favoritePaths: library.favoritePaths
        columnProfile: "artist"
        showArtistColumn: false
        showArtwork: true
        canFavorite: true
        canQueue: library.canQueueTracks
        canAddToPlaylist: library.canAddTracksToPlaylists
        canInspect: true
        canNavigateEntities: true
        onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
        onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
        onQueueRequested: trackId => library.queue_track_by_id(trackId)
        onAddToPlaylistRequested: path => root.addToPlaylistRequested(path)
        onPropertiesRequested: track => trackPropertiesView.inspect(track)
        onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    }

    TrackPropertiesView { id: trackPropertiesView }

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
