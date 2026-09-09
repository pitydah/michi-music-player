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

    property var inspectedTrack: null
    property int inspectedIndex: -1

    readonly property var albumFacts: library.albumPresentation || ({})
    readonly property bool showMetricRail: MichiBreakpoints.atLeastWide(root.width)
    readonly property string preciseDurationText: root.formatDurationPrecise(
        library.albumDurationMs)
    readonly property string sampleRateText: root.formatSampleRate(
        albumFacts.maxSampleRateHz || 0)
    readonly property string channelsText: root.formatChannels(
        albumFacts.maxChannels || 0)
    readonly property string heroTechnicalText: root.compactTechnicalSummary(
        library.albumTechnicalSummary || "")
    readonly property var heroMetricRows: [
        { label: qsTr("TRACKS"), value: String(library.albumTracks.length) },
        { label: qsTr("DURATION"), value: root.preciseDurationText },
        { label: qsTr("SAMPLE RATE"), value: root.sampleRateText },
        { label: qsTr("CHANNELS"), value: root.channelsText },
        { label: qsTr("DISCS"), value: albumFacts.discCount > 1
            ? String(albumFacts.discCount) : "" }
    ].filter(function(row) { return row.value.length > 0 })

    AlbumPaletteBinding { id: paletteBinding; album: root.albumFacts }

    readonly property var inspectorRows: inspectedTrack ? [
        { label: qsTr("Format"), value: inspectedTrack.codec || qsTr("Unknown") },
        { label: qsTr("Sample rate"), value: root.formatSampleRate(
            inspectedTrack.sampleRateHz || 0) || qsTr("Unknown") },
        { label: qsTr("Bit depth"), value: root.formatBitDepth(
            inspectedTrack.bitDepth || 0, inspectedTrack.codec || "") },
        { label: qsTr("Channels"), value: root.formatChannels(
            inspectedTrack.channels || 0) || qsTr("Unknown") },
        { label: qsTr("File size"), value: root.formatFileSize(inspectedTrack.fileSize) },
        { label: qsTr("Path"), value: inspectedTrack.path }
    ] : []

    visible: library.selectedAlbumKey !== ""
    focus: visible
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    /* Opening detail is deliberately CACHE ONLY.  This invariant is part of
     * R16: passive navigation must never start provider/network work. */
    readonly property string selectedAlbumKey: library.selectedAlbumKey
    onSelectedAlbumKeyChanged: {
        if (root.selectedAlbumKey.length > 0)
            enrichment.open_album_cached(root.selectedAlbumKey)
    }

    Keys.onEscapePressed: function(event) {
        library.clear_album_selection()
        event.accepted = true
    }

    onVisibleChanged: {
        if (!visible) {
            inspectedTrack = null
            inspectedIndex = -1
        }
    }

    function _albumIndexFor(row) {
        for (var i = 0; i < library.albumTracks.length; ++i) {
            if (library.albumTracks[i].path === row.path)
                return i
        }
        return -1
    }

    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0)
            return qsTr("Unknown")
        if (bytes >= 1073741824)
            return (bytes / 1073741824).toFixed(2) + " GB"
        return (bytes / 1048576).toFixed(1) + " MB"
    }

    function formatDurationPrecise(milliseconds) {
        var totalSeconds = Math.max(0, Math.floor((milliseconds || 0) / 1000))
        if (totalSeconds <= 0)
            return ""
        var seconds = totalSeconds % 60
        var totalMinutes = Math.floor(totalSeconds / 60)
        var minutes = totalMinutes % 60
        var hours = Math.floor(totalMinutes / 60)
        function two(value) { return value < 10 ? "0" + value : String(value) }
        if (hours > 0)
            return hours + ":" + two(minutes) + ":" + two(seconds)
        return totalMinutes + ":" + two(seconds)
    }

    function formatSampleRate(hz) {
        var numeric = Number(hz || 0)
        if (numeric <= 0)
            return ""
        if (numeric >= 1000) {
            var khz = Math.round((numeric / 1000) * 10) / 10
            return String(khz) + " kHz"
        }
        return String(Math.round(numeric)) + " Hz"
    }

    function formatChannels(channels) {
        var count = Number(channels || 0)
        if (count <= 0)
            return ""
        if (count === 1)
            return qsTr("Mono")
        if (count === 2)
            return qsTr("Stereo")
        return qsTr("%1 ch").arg(count)
    }

    function _lossyCodec(codec) {
        var normalized = String(codec || "").toLowerCase()
        return normalized.indexOf("mp3") >= 0
            || normalized.indexOf("mpeg") >= 0
            || normalized.indexOf("aac") >= 0
            || normalized.indexOf("vorbis") >= 0
            || normalized.indexOf("opus") >= 0
    }

    function formatBitDepth(bits, codec) {
        var value = Number(bits || 0)
        if (value > 0)
            return value + "-bit"
        return root._lossyCodec(codec) ? qsTr("N/A") : qsTr("Unknown")
    }

    function compactTechnicalSummary(summary) {
        var raw = String(summary || "")
        if (raw.length === 0 || !root.showMetricRail)
            return raw
        // Wide layout owns sample rate in the metric rail.  Strip only that
        // presentation fragment from the canonical summary; format/codec,
        // bitrate, bit depth and Mixed formats remain untouched.
        return raw.split(" · ").filter(function(segment) {
            return segment.toLowerCase().indexOf("hz") < 0
        }).join(" · ")
    }

    // One compact navigation authority.  LibraryHeader already owns the
    // global "Library" identity, and the hero owns the album title.
    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.sm

        MichiButton {
            text: qsTr("Albums")
            iconName: "back"
            variant: "ghost"
            onClicked: library.clear_album_selection()
        }
        Item { Layout.fillWidth: true }
    }

    // ── Album identity / primary action ────────────────────────────────
    MichiGlassSurface {
        objectName: "albumHeroSurface"
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Layout.preferredHeight: heroContent.implicitHeight
            + root.heroPadding * 2
        elevation: "elevated"
        contentPadding: root.heroPadding
        accented: true
        accentColor: paletteBinding.value.accentSafe || MichiPalette.auroraBlue
        textured: true
        materialRole: MichiMaterialRole.hero
        glintMode: "michi"
        readonly property int heroPadding: root.width < MichiBreakpoints.mediumMin
            ? MichiSpacing.md : MichiSpacing.lg

        Rectangle {
            anchors.fill: parent
            radius: MichiRadius.lg
            opacity: 0.22
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
            spacing: root.width < MichiBreakpoints.mediumMin
                ? MichiSpacing.md : MichiSpacing.xl

            Artwork {
                sourcePath: library.albumArtwork.length > 0
                    ? library.albumArtwork : enrichment.albumArtworkPath
                fallbackText: library.albumTitle
                Layout.preferredWidth: Math.min(204,
                    Math.max(136, root.width * 0.15))
                Layout.preferredHeight: Layout.preferredWidth
                Layout.alignment: Qt.AlignTop
                requestedSize: 512
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.alignment: Qt.AlignTop
                spacing: MichiSpacing.xs

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
                        ? library.albumYear : ""].filter(function(value) {
                            return String(value).length > 0
                        }).join(" · ")
                    role: "secondary"
                    color: MichiPalette.textMuted
                    visible: text.length > 0
                    elide: Text.ElideRight
                }

                MichiText {
                    Layout.fillWidth: true
                    Layout.topMargin: MichiSpacing.xs
                    text: root.heroTechnicalText
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                    visible: text.length > 0
                    elide: Text.ElideRight
                }

                RowLayout {
                    Layout.topMargin: MichiSpacing.md
                    spacing: MichiSpacing.sm

                    MichiButton {
                        text: qsTr("Play album")
                        iconName: "play"
                        variant: "primary"
                        enabled: library.albumTracks.length > 0
                        onClicked: library.play_selected_album()
                    }

                    MichiIconButton {
                        id: albumMoreButton
                        iconName: "more"
                        accessibleName: qsTr("More album options")
                        onClicked: albumDetailMenu.popup()

                        AlbumContextMenu {
                            id: albumDetailMenu
                            x: Math.max(0, parent.width - width)
                            y: parent.height + MichiSpacing.xs
                            album: root.albumFacts
                            showOpenAction: false
                            // Productive LibraryContentHost consumes these
                            // Bridge intents; retain fail-closed gating inside
                            // the shared menu for the backend capabilities.
                            canAddToPlaylist: true
                            canCreatePlaylist: true
                            canShowProperties: true
                        }
                    }
                }
            }

            Rectangle {
                visible: root.showMetricRail
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                Layout.topMargin: MichiSpacing.xs
                Layout.bottomMargin: MichiSpacing.xs
                color: MichiSemanticColors.borderSubtle
            }

            GridLayout {
                visible: root.showMetricRail
                Layout.preferredWidth: 252
                Layout.minimumWidth: 220
                Layout.alignment: Qt.AlignTop
                columns: 2
                columnSpacing: MichiSpacing.xl
                rowSpacing: MichiSpacing.md

                Repeater {
                    model: root.heroMetricRows
                    delegate: ColumnLayout {
                        id: metricDelegate
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: MichiSpacing.xxs

                        MichiText {
                            text: metricDelegate.modelData.label
                            role: "technical"
                            technical: true
                            color: MichiPalette.textMuted
                        }
                        MichiText {
                            Layout.fillWidth: true
                            text: metricDelegate.modelData.value
                            role: "secondary"
                            font.weight: Font.Medium
                            color: MichiPalette.textPrimary
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    // ── Editorial knowledge / Library Enrichment ───────────────────────
    RowLayout {
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        spacing: MichiSpacing.md

        MichiText {
            text: qsTr("About this album")
            role: "section"
        }

        EnrichmentInlineState {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
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
    }

    EnrichmentKnowledgeCard {
        objectName: "albumKnowledgeCard"
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        title: qsTr("About this album")
        knowledge: enrichment.albumKnowledge
        hasKnowledge: enrichment.albumHasKnowledge
        sources: enrichment.albumAttributions
        materialRole: MichiMaterialRole.editorial
        elevation: "subtle"
        shadowed: false
        // The card already owns one lg inset internally.  Avoid the old
        // double-padding that made the album information block balloon.
        contentPadding: 0
    }

    MichiText {
        Layout.fillWidth: true
        Layout.leftMargin: MichiSpacing.xs
        Layout.rightMargin: MichiSpacing.xs
        visible: enrichment.activeKind === "album"
            && !enrichment.albumHasKnowledge
        text: enrichment.onlineEnabled
            ? qsTr("No additional album information has been fetched yet.")
            : qsTr("Online album information is disabled. Local metadata remains available.")
        role: "secondary"
        color: MichiPalette.textMuted
        wrapMode: Text.WordWrap
    }

    InspectorPanel {
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 160 : 0
        Layout.maximumHeight: 160
        visible: root.inspectedTrack !== null
            && !MichiBreakpoints.atLeastMedium(root.width)
        title: root.inspectedTrack ? root.inspectedTrack.title : qsTr("Track information")
        rows: root.inspectorRows
        onCloseRequested: {
            root.inspectedTrack = null
            root.inspectedIndex = -1
        }
    }

    // ── Primary album content: tracks ──────────────────────────────────
    MichiText {
        text: qsTr("Tracks")
        role: "section"
    }

    RowLayout {
        id: trackArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: Math.min(190,
            Math.max(144, root.height * 0.24))
        spacing: MichiSpacing.lg

        MichiGlassSurface {
            objectName: "albumTrackTableSurface"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 0
            elevation: "subtle"
            contentPadding: 0
            shadowed: false
            textured: false

            MichiTrackTable {
                id: albumTracksTable
                objectName: "albumTracksTable"
                anchors.fill: parent
                rows: library.albumTracks
                playingPath: typeof playback !== "undefined" && playback
                    ? playback.currentPath : ""
                favoriteTrackIds: library.favoriteTrackIds
                favoritePaths: library.favoritePaths
                // Album identity and artwork are already authoritative in
                // the hero.  Repeating cover thumbnails in every track row
                // wastes width and is a major source of horizontal overflow.
                columnProfile: "album"
                numberingMode: "disc-track"
                showArtwork: false
                showArtistColumn: true
                showAlbumColumn: false
                canFavorite: true
                canQueue: library.canQueueTracks
                canAddToPlaylist: library.canAddTracksToPlaylists
                canNavigateEntities: true
                canInspect: true
                canAddToNewPlaylist: true
                selectedIndex: root.inspectedTrack !== null
                    ? root.inspectedIndex : -1

                // Keep the canonical TrackId-first action seams intact.
                onTrackActivated: (trackId, path, index) =>
                    library.activate_album_track_by_id(trackId)
                onFavoriteRequested: trackId =>
                    library.toggle_favorite_by_id(trackId)
                onQueueRequested: trackId => library.queue_track_by_id(trackId)
                onAddToPlaylistRequested: (trackId, path) =>
                    library.request_tracks_playlist_target([trackId])
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
            title: root.inspectedTrack ? root.inspectedTrack.title : qsTr("Track information")
            rows: root.inspectorRows
            onCloseRequested: {
                root.inspectedTrack = null
                root.inspectedIndex = -1
            }
        }
    }

    /* Manual review remains the same productive enrichment seam. */
    ReviewMatchesDialog {
        id: reviewDialog
        visible: enrichment.reviewOpen && enrichment.reviewKind === "album"
        kind: "album"
        loading: enrichment.reviewLoading
        errorText: enrichment.reviewError
        albumCandidates: enrichment.albumCandidates
        onlineEnabled: enrichment.onlineEnabled
        onSearchRequested: function(name) { enrichment.search_album(name, "") }
        onAlbumSearchRequested: function(title, artistName) {
            enrichment.search_album(title, artistName)
        }
        onConfirmAlbum: function(id) { enrichment.confirm_album_candidate(id) }
        onClosed: enrichment.close_review()
    }
}
