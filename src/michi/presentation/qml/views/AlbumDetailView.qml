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
    objectName: "albumDetailView"

    property string addTargetPath: ""
    property var inspectedTrack: null
    readonly property var inspectorRows: inspectedTrack ? [
        { label: "Format", value: inspectedTrack.codec || "Unknown" },
        { label: "Sample rate", value: inspectedTrack.sampleRateHz > 0
            ? (inspectedTrack.sampleRateHz / 1000) + " kHz" : "Unknown" },
        { label: "Bit depth", value: inspectedTrack.bitDepth > 0
            ? inspectedTrack.bitDepth + "-bit" : "Unknown" },
        { label: "Channels", value: inspectedTrack.channels > 0
            ? String(inspectedTrack.channels) : "Unknown" },
        { label: "File size", value: root.formatFileSize(inspectedTrack.fileSize) },
        { label: "Path", value: inspectedTrack.path }
    ] : []

    visible: library.selectedAlbumKey !== ""
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    /* M6.9: explicit detail activation drives enrichment for the
     * selected album — never lists/search/scan. */
    readonly property string selectedAlbumKey: library.selectedAlbumKey
    onSelectedAlbumKeyChanged: {
        if (root.selectedAlbumKey.length > 0)
            enrichment.activate_album(root.selectedAlbumKey)
    }

    onVisibleChanged: if (!visible) inspectedTrack = null

    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0)
            return "Unknown"
        if (bytes >= 1073741824)
            return (bytes / 1073741824).toFixed(2) + " GB"
        return (bytes / 1048576).toFixed(1) + " MB"
    }

    function formatDuration(milliseconds) {
        var seconds = Math.max(0, Math.floor(milliseconds / 1000))
        var minutes = Math.floor(seconds / 60)
        var hours = Math.floor(minutes / 60)
        var remainingMinutes = minutes % 60
        if (hours > 0)
            return hours + " hr " + remainingMinutes + " min"
        return minutes + " min"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.sm

        MichiButton {
            text: "Back"
            iconName: "back"
            variant: "ghost"
            onClicked: library.clear_album_selection()
        }
        MichiText {
            text: "Library"
            role: "secondary"
            color: MichiPalette.textMuted
        }
        MichiText {
            text: "›"
            role: "secondary"
            color: MichiPalette.textMuted
        }
        MichiText {
            Layout.fillWidth: true
            text: library.albumTitle
            role: "secondary"
            color: MichiPalette.textSecondary
            elide: Text.ElideRight
        }
    }

    MichiGlassSurface {
        objectName: "albumHeroSurface"
        Layout.fillWidth: true
        Layout.preferredHeight: heroContent.implicitHeight + MichiSpacing.xl * 2
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
                Layout.preferredWidth: Math.min(232, Math.max(164, root.width * .19))
                Layout.preferredHeight: Layout.preferredWidth
                Layout.alignment: Qt.AlignTop
                requestedSize: 512
            }

            ColumnLayout {
                Layout.fillWidth: true
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
                        ? library.albumYear : ""].filter(value => value !== "").join(" · ")
                    role: "secondary"
                    visible: text.length > 0
                }

                RowLayout {
                    spacing: MichiSpacing.sm
                    AudioQualityBadge { label: library.albumTechnicalSummary }
                    MichiStatusChip {
                        text: library.albumTracks.length
                            + (library.albumTracks.length === 1 ? " track" : " tracks")
                        tone: "neutral"
                        dotVisible: false
                    }
                    MichiStatusChip {
                        text: root.formatDuration(library.albumDurationMs)
                        tone: "neutral"
                        dotVisible: false
                        visible: library.albumDurationMs > 0
                    }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    spacing: MichiSpacing.sm
                    MichiButton {
                        text: "Play album"
                        iconName: "play"
                        enabled: library.albumTracks.length > 0
                        onClicked: library.activate_album_track(0)
                    }
                }
            }

            Rectangle {
                visible: root.width >= 960
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                Layout.topMargin: MichiSpacing.sm
                Layout.bottomMargin: MichiSpacing.sm
                color: MichiSemanticColors.borderSubtle
            }

            ColumnLayout {
                visible: root.width >= 960
                Layout.preferredWidth: 178
                Layout.alignment: Qt.AlignTop
                spacing: MichiSpacing.md

                ColumnLayout {
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: "DURATION"
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    MichiText {
                        text: root.formatDuration(library.albumDurationMs)
                        role: "secondary"
                    }
                }
                ColumnLayout {
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: "TRACKS"
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    MichiText {
                        text: library.albumTracks.length
                        role: "secondary"
                    }
                }
                ColumnLayout {
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: "LIBRARY QUALITY"
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: library.albumTechnicalSummary || "Standard"
                        role: "secondary"
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }

    /* M6.9 — online knowledge surface (complementary to the canonical
     * local metadata; local album facts stay authoritative). */
    EnrichmentStatusBar {
        Layout.fillWidth: true
        state: enrichment.state
        message: enrichment.stateMessage
        busy: enrichment.busy
        visible: enrichment.activeKind === "album"
    }

    EnrichmentKnowledgeCard {
        Layout.fillWidth: true
        title: "About this album"
        knowledge: enrichment.albumKnowledge
        hasKnowledge: enrichment.albumHasKnowledge
        sources: enrichment.albumAttributions
        visible: enrichment.activeKind === "album"
    }

    EnrichmentActions {
        Layout.fillWidth: true
        kind: "album"
        state: enrichment.state
        onlineEnabled: enrichment.onlineEnabled
        hasKnowledge: enrichment.albumHasKnowledge
        visible: enrichment.activeKind === "album"
        onRefreshRequested: enrichment.refresh_album()
        onReviewRequested: enrichment.open_review("album")
        onClearRequested: enrichment.clear_knowledge()
        onResetRequested: enrichment.reset_identity()
    }

    InspectorPanel {
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 210 : 0
        visible: root.inspectedTrack !== null && root.width < 760
        title: root.inspectedTrack ? root.inspectedTrack.title : "Track information"
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

            ListView {
                id: albumTracksList
                anchors.fill: parent
                model: library.albumTracks
                clip: true
                spacing: MichiSpacing.xs
                boundsBehavior: Flickable.StopAtBounds
                headerPositioning: ListView.InlineHeader

                header: TrackTableHeader {
                    width: albumTracksList.width
                    showAlbumColumn: false
                    actionColumnWidth: 116
                }

                delegate: TrackRow {
                    required property int index
                    required property var modelData
                    width: albumTracksList.width
                    numberText: modelData.discNumber > 1
                        ? modelData.discNumber + "." + modelData.trackNumber
                        : String(modelData.trackNumber > 0
                            ? modelData.trackNumber : index + 1)
                    title: modelData.title || modelData.displayName
                    artist: modelData.artist
                    showAlbumColumn: false
                    durationMs: modelData.durationMs
                    quality: modelData.qualityLabel
                    playing: playback.currentPath === modelData.path
                    favorite: library.favoritePaths.indexOf(modelData.path) !== -1
                    showFavorite: true
                    showAddToPlaylist: true
                    showInspector: true
                    selected: root.inspectedTrack
                        && root.inspectedTrack.path === modelData.path
                    onActivated: library.activate_album_track(index)
                    onFavoriteToggled: library.toggle_favorite(modelData.path)
                    onAddToPlaylistRequested: root.addTargetPath = modelData.path
                    onInspectorRequested: root.inspectedTrack = modelData
                }
            }
        }

        InspectorPanel {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            visible: root.inspectedTrack !== null && root.width >= 760
            title: root.inspectedTrack ? root.inspectedTrack.title : "Track information"
            rows: root.inspectorRows
            onCloseRequested: root.inspectedTrack = null
        }
    }

    /* M6.9 — manual review dialog */
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
