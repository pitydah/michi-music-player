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
    property int inspectedIndex: -1

    function _albumIndexFor(row) {
        for (var i = 0; i < library.albumTracks.length; ++i) {
            if (library.albumTracks[i].path === row.path)
                return i
        }
        return -1
    }
    readonly property var albumFacts: library.albumPresentation || ({})
    AlbumPaletteBinding { id: paletteBinding; album: root.albumFacts }
    readonly property var albumFactRows: [
        { label: "Format", value: albumFacts.codecs && albumFacts.codecs.length
            ? albumFacts.codecs.join(" · ") : "Unknown" },
        { label: "Sample rate", value: albumFacts.maxSampleRateHz > 0
            ? (albumFacts.maxSampleRateHz / 1000) + " kHz" : "Unknown" },
        { label: "Bit depth", value: albumFacts.maxBitDepth > 0
            ? albumFacts.maxBitDepth + "-bit" : "Unknown" },
        { label: "Channels", value: albumFacts.maxChannels > 0
            ? String(albumFacts.maxChannels) : "Unknown" },
        { label: qsTr("Discs"), value: albumFacts.discCount > 0
            ? String(albumFacts.discCount) : "Unknown" },
        { label: qsTr("Classification"), value: albumFacts.containsDsd ? "DSD"
            : albumFacts.containsHighResolution ? "High-resolution PCM"
            : albumFacts.technicalState === "homogeneous" ? "Consistent"
            : albumFacts.technicalState === "mixed" ? "Mixed formats" : "Standard" }
    ]
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
    focus: visible
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    /* Opening detail is passive: it may hydrate an existing local cache but
     * never starts a network operation. Refresh/review below are explicit. */
    readonly property string selectedAlbumKey: library.selectedAlbumKey
    onSelectedAlbumKeyChanged: {
        if (root.selectedAlbumKey.length > 0)
            enrichment.open_album_cached(root.selectedAlbumKey)
    }

    Keys.onEscapePressed: function(event) {
        library.clear_album_selection()
        event.accepted = true
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
        accentColor: paletteBinding.value.accentSafe || MichiPalette.auroraBlue
        textured: true
        materialRole: MichiMaterialRole.hero
        glintMode: "michi"

        Rectangle {
            anchors.fill: parent
            radius: MichiRadius.lg
            opacity: 0.34
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0
                    color: paletteBinding.value.dominant || MichiPalette.playlistHeroTop
                }
                GradientStop {
                    position: 1
                    color: paletteBinding.value.backplane || MichiPalette.playlistHeroBottom
                }
            }
            Behavior on opacity {
                enabled: !MichiAccessibility.reducedMotion
                NumberAnimation { duration: MichiMotion.paletteCrossfade }
            }
        }

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
                        text: qsTr("Play album")
                        iconName: "play"
                        enabled: library.albumTracks.length > 0
                        onClicked: library.play_selected_album()
                    }
                }
            }

            Rectangle {
                visible: MichiBreakpoints.atLeastWide(root.width)
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                Layout.topMargin: MichiSpacing.sm
                Layout.bottomMargin: MichiSpacing.sm
                color: MichiSemanticColors.borderSubtle
            }

            ColumnLayout {
                visible: MichiBreakpoints.atLeastWide(root.width)
                Layout.preferredWidth: 178
                Layout.alignment: Qt.AlignTop
                spacing: MichiSpacing.md

                ColumnLayout {
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: qsTr("DURATION")
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
                        text: qsTr("TRACKS")
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

    GridLayout {
        Layout.fillWidth: true
        columns: MichiBreakpoints.atLeastWide(root.width) ? 2 : 1
        columnSpacing: MichiSpacing.lg
        rowSpacing: MichiSpacing.lg
        visible: enrichment.activeKind === "album"

        EnrichmentKnowledgeCard {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            title: "About this album"
            knowledge: enrichment.albumKnowledge
            hasKnowledge: enrichment.albumHasKnowledge
            sources: enrichment.albumAttributions
            materialRole: MichiMaterialRole.editorial
        }

        MichiGlassSurface {
            objectName: "albumTechnicalFacts"
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            implicitHeight: factsColumn.implicitHeight + MichiSpacing.lg * 2
            materialRole: MichiMaterialRole.control
            contentPadding: MichiSpacing.lg
            shadowed: false

            ColumnLayout {
                id: factsColumn
                anchors.fill: parent
                anchors.margins: MichiSpacing.lg
                spacing: MichiSpacing.md

                MichiText {
                    text: "Album facts"
                    role: "section"
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: MichiBreakpoints.atLeastMedium(root.width) ? 2 : 1
                    columnSpacing: MichiSpacing.xl
                    rowSpacing: MichiSpacing.sm

                    Repeater {
                        model: root.albumFactRows
                        delegate: ColumnLayout {
                            id: albumFactDelegate
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: MichiSpacing.xxs
                            MichiText {
                                text: albumFactDelegate.modelData.label.toUpperCase()
                                role: "technical"
                                technical: true
                                color: MichiPalette.textMuted
                            }
                            MichiText {
                                Layout.fillWidth: true
                                text: albumFactDelegate.modelData.value
                                role: "secondary"
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
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
        visible: root.inspectedTrack !== null
            && !MichiBreakpoints.atLeastMedium(root.width)
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

            MichiTrackTable {
                id: albumTracksTable
                objectName: "albumTracksTable"
                anchors.fill: parent
                rows: library.albumTracks
                playingPath: typeof playback !== "undefined" && playback ? playback.currentPath : ""
                favoriteTrackIds: library.favoriteTrackIds
                favoritePaths: library.favoritePaths
                // LIB-A §8/22: perfil de álbum (álbum implícito en el
                // contexto de página) + numeración disco-track.
                columnProfile: "album"
                numberingMode: "disc-track"
                showArtistColumn: true
                showAlbumColumn: false
                canFavorite: true
                canQueue: library.canQueueTracks
                canNavigateEntities: true
                // LIB-A §25: el InspectorPanel REAL existe en esta vista.
                canInspect: true
                selectedIndex: root.inspectedTrack !== null
                    ? root.inspectedIndex : -1
                // TrackId-first (el Bridge resuelve legacy-path::).
                onTrackActivated: (trackId, path, index) =>
                    library.activate_album_track_by_id(trackId)
                onFavoriteRequested: trackId =>
                    library.toggle_favorite_by_id(trackId)
                onQueueRequested: trackId => library.queue_track_by_id(trackId)
                onGoToArtistRequested: artistKey =>
                    library.select_artist(artistKey)
                onPropertiesRequested: modelData => {
                    root.inspectedTrack = modelData
                    root.inspectedIndex = root._albumIndexFor(modelData)
                }
            }
        }

        InspectorPanel {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            visible: root.inspectedTrack !== null
                && MichiBreakpoints.atLeastMedium(root.width)
            title: root.inspectedTrack ? root.inspectedTrack.title : "Track information"
            rows: root.inspectorRows
            onCloseRequested: {
                root.inspectedTrack = null
                root.inspectedIndex = -1
            }
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
