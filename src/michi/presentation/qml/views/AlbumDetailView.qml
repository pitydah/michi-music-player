import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../enrichment"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    objectName: "albumDetailView"

    signal addToPlaylistRequested(string path)
    property var inspectedTrack: null
    readonly property var inspectorRows: inspectedTrack ? [
        { label: "Format", value: inspectedTrack.codec || "Unknown" },
        { label: "Sample rate", value: inspectedTrack.sampleRateHz > 0
            ? (inspectedTrack.sampleRateHz / 1000) + " kHz" : "Unknown" },
        { label: "Bit depth", value: inspectedTrack.bitDepth > 0
            ? inspectedTrack.bitDepth + "-bit" : "Unknown" },
        { label: "Channels", value: inspectedTrack.channels > 0
            ? String(inspectedTrack.channels) : "Unknown" },
        { label: "File size", value: MichiFormat.formatFileSize(inspectedTrack.fileSize) },
        { label: "Path", value: inspectedTrack.path }
    ] : []
    readonly property string selectedAlbumKey: library.selectedAlbumKey

    visible: library.selectedAlbumKey !== ""
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    onSelectedAlbumKeyChanged: {
        if (root.selectedAlbumKey.length > 0)
            enrichment.activate_album(root.selectedAlbumKey)
    }
    onVisibleChanged: if (!visible) inspectedTrack = null

    MichiButton {
        text: qsTr("Albums")
        iconName: "back"
        variant: "ghost"
        Layout.alignment: Qt.AlignLeft
        accessibleName: qsTr("Back to Albums")
        onClicked: library.clear_album_selection()
    }

    Flickable {
        id: summaryFlick
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(summaryColumn.implicitHeight,
            Math.max(220, Math.min(root.height - 180, root.height * 0.54)))
        contentWidth: width
        contentHeight: summaryColumn.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: MichiScrollBar { }

        Column {
            id: summaryColumn
            width: summaryFlick.width
            spacing: MichiThemeState.contentGap

            MichiGlassSurface {
                objectName: "albumHeroSurface"
                width: parent.width
                implicitHeight: heroContent.implicitHeight + MichiSpacing.xl * 2
                elevation: "elevated"
                contentPadding: MichiSpacing.xl
                accented: true
                accentColor: MichiPalette.auroraBlue
                textured: true

                RowLayout {
                    id: heroContent
                    anchors.fill: parent
                    spacing: MichiSpacing.xl

                    Artwork {
                        sourcePath: library.albumArtwork.length > 0
                            ? library.albumArtwork : enrichment.albumArtworkPath
                        fallbackText: library.albumTitle
                        Layout.preferredWidth: Math.min(220,
                            Math.max(156, root.width * 0.18))
                        Layout.preferredHeight: Layout.preferredWidth
                        Layout.alignment: Qt.AlignTop
                        requestedSize: 512
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: MichiSpacing.sm

                        MichiText {
                            Layout.fillWidth: true
                            text: library.albumTitle
                            role: "display"
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                        MichiText {
                            Layout.fillWidth: true
                            text: library.albumArtist
                            role: "section"
                            color: MichiPalette.textSecondary
                            elide: Text.ElideRight
                        }
                        MichiText {
                            Layout.fillWidth: true
                            text: [library.albumGenres, library.albumYear > 0
                                ? library.albumYear : ""].filter(
                                    value => value !== "").join(" · ")
                            role: "secondary"
                            visible: text.length > 0
                        }

                        RowLayout {
                            spacing: MichiSpacing.sm
                            AudioQualityBadge {
                                label: library.albumTechnicalSummary
                                visible: label.length > 0
                            }
                            MichiText {
                                text: library.albumTracks.length
                                    + (library.albumTracks.length === 1
                                        ? qsTr(" track") : qsTr(" tracks"))
                                    + (library.albumDurationMs > 0
                                        ? " · " + MichiFormat.formatHoursMinutes(
                                            library.albumDurationMs) : "")
                                role: "secondary"
                                color: MichiPalette.textMuted
                            }
                        }

                        Item { Layout.fillHeight: true }

                        MichiButton {
                            text: qsTr("Play album")
                            iconName: "play"
                            enabled: library.albumTracks.length > 0
                            onClicked: library.activate_album_track(0)
                        }
                    }
                }
            }

            EnrichmentInlineState {
                width: parent.width
                kind: "album"
                state: enrichment.state
                message: enrichment.stateMessage
                busy: enrichment.busy
                onlineEnabled: enrichment.onlineEnabled
                hasKnowledge: enrichment.albumHasKnowledge
                active: enrichment.activeKind === "album"
                onRefreshRequested: enrichment.refresh_album()
                onReviewRequested: enrichment.open_review("album")
                onClearRequested: enrichment.clear_knowledge()
                onResetRequested: enrichment.reset_identity()
            }

            EnrichmentKnowledgeCard {
                width: parent.width
                title: qsTr("About this album")
                knowledge: enrichment.albumKnowledge
                hasKnowledge: enrichment.albumHasKnowledge
                sources: enrichment.albumAttributions
                visible: enrichment.activeKind === "album" && enrichment.albumHasKnowledge
            }
        }
    }

    InspectorPanel {
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 210 : 0
        visible: root.inspectedTrack !== null && root.width < 760
        title: root.inspectedTrack ? root.inspectedTrack.title : qsTr("Track information")
        rows: root.inspectorRows
        onCloseRequested: root.inspectedTrack = null
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: MichiSpacing.lg

        MichiGlassSurface {
            objectName: "albumTrackTableSurface"
            Layout.fillWidth: true
            Layout.fillHeight: true
            elevation: "subtle"
            contentPadding: MichiSpacing.sm
            shadowed: false
            textured: false

            MichiTrackTable {
                id: albumTracksTable
                anchors.fill: parent
                rows: library.albumTracks
                playingPath: playback.currentPath
                favoritePaths: library.favoritePaths
                columnProfile: "album"
                showAlbumColumn: false
                showArtwork: false
                numberingMode: "disc-track"
                canFavorite: true
                canQueue: library.canQueueTracks
                canAddToPlaylist: library.canAddTracksToPlaylists
                canInspect: true
                canNavigateEntities: true
                // P1-07: Album Detail keeps ALBUM playback context — the
                // application coordinator owns TrackId membership.
                onTrackActivated: (trackId, path, index) => library.activate_album_track(index)
                onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
                onQueueRequested: trackId => library.queue_track_by_id(trackId)
                onAddToPlaylistRequested: trackId => root.addToPlaylistRequested(path)
                onPropertiesRequested: track => root.inspectedTrack = track
                onGoToArtistRequested: artistKey => library.select_artist(artistKey)
            }
        }

        InspectorPanel {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            visible: root.inspectedTrack !== null && root.width >= 760
            title: root.inspectedTrack ? root.inspectedTrack.title : qsTr("Track information")
            rows: root.inspectorRows
            onCloseRequested: root.inspectedTrack = null
        }
    }

    ReviewMatchesDialog {
        id: reviewDialog
        visible: enrichment.reviewOpen && enrichment.reviewKind === "album"
        kind: "album"
        loading: enrichment.reviewLoading
        errorText: enrichment.reviewError
        albumCandidates: enrichment.albumCandidates
        onlineEnabled: enrichment.onlineEnabled
        onSearchRequested: function (name) { enrichment.search_album(name, "") }
        onAlbumSearchRequested: function (title, artistName) {
            enrichment.search_album(title, artistName)
        }
        onConfirmAlbum: function (id) { enrichment.confirm_album_candidate(id) }
        onClosed: enrichment.close_review()
    }
}
