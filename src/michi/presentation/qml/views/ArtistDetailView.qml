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
    property string addTargetPath: ""
    readonly property string selectedArtistKey: library.selectedArtistKey

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap
    visible: library.selectedArtistKey !== ""

    onSelectedArtistKeyChanged: {
        if (root.selectedArtistKey.length > 0)
            enrichment.activate_artist(root.selectedArtistKey)
    }

    MichiButton {
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
        Layout.preferredHeight: Math.min(summaryColumn.implicitHeight,
            Math.max(280, root.height * 0.67))
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
                width: parent.width
                height: visible ? 244 : 0
                visible: library.artistAlbums.length > 0
                model: library.artistAlbums
                orientation: ListView.Horizontal
                spacing: MichiSpacing.sm
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.horizontal: MichiScrollBar { }
                Accessible.role: Accessible.List
                Accessible.name: qsTr("Albums by this artist")
                delegate: AlbumCard {
                    required property var modelData
                    width: 166
                    height: 236
                    album: modelData
                    onActivated: library.select_album(modelData.key)
                }
            }
        }
    }

    MichiText {
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
        onTrackActivated: (path, _index) => library.activate_path(path)
        onFavoriteRequested: path => library.toggle_favorite(path)
        onQueueRequested: path => library.queue_track(path)
        onAddToPlaylistRequested: path => root.addTargetPath = path
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
