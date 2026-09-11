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
    readonly property string preciseDurationText: MichiFormat.formatDuration(
        library.albumDurationMs)
    readonly property string technicalSummaryText: library.albumTechnicalSummary || ""
    readonly property string channelsText: root.albumChannelsText()
    readonly property string compactAlbumSummary: root.albumSummaryText()
    readonly property var heroMetricRows: [
        { label: qsTr("TRACKS"), value: String(library.albumTracks.length) },
        { label: qsTr("DURATION"), value: root.preciseDurationText },
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
        { label: qsTr("File size"), value: MichiFormat.formatFileSize(
            inspectedTrack.fileSize) },
        { label: qsTr("Path"), value: inspectedTrack.path }
    ] : []

    visible: library.selectedAlbumKey !== ""
    focus: visible
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    /* Opening detail is deliberately CACHE ONLY. Passive navigation must
     * never start provider/network work. Explicit refresh/review below are
     * the only network-capable presentation intents. */
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

    function albumChannelsText() {
        var tracks = library.albumTracks || []
        if (tracks.length === 0)
            return ""
        var channelCount = 0
        for (var i = 0; i < tracks.length; ++i) {
            var current = Number(tracks[i].channels || 0)
            // An unknown member makes an album-wide channel claim unsafe.
            if (current <= 0)
                return ""
            if (channelCount === 0)
                channelCount = current
            else if (channelCount !== current)
                return qsTr("Mixed")
        }
        return root.formatChannels(channelCount)
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

    function albumSummaryText() {
        var count = library.albumTracks.length
        var countText = qsTr("%1 track").arg(count)
        if (count !== 1)
            countText = qsTr("%1 tracks").arg(count)
        if (root.preciseDurationText.length === 0)
            return countText
        return countText + " · " + root.preciseDurationText
    }

    // LibraryHeader owns the page identity and the hero owns album identity.
    // Keep navigation to one compact, unambiguous back affordance.
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

    /* Context region is independently scrollable. At minimum-height windows
     * it keeps the conservative 42% budget that protects the track table.
     * Once there is normal desktop height, it may use 54% (still capped at
     * 440 px) so cached/factual album information is actually visible
     * instead of forcing an immediate nested scroll. */
    MichiScrollView {
        id: albumContextScroll
        objectName: "albumContextScroll"
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        // R7-13: el root recibe su height DEL LAYOUT del host: medirlo
        // aquí realimenta el arrange (el scroll define su altura por
        // layout → root.height → boundedHeight → layout) y Qt lo aborta
        // como "recursive rearrange". La ventana es estable y preserva el
        // presupuesto 42/54% (80..440px); el contenido scrollea interno.
        readonly property real contextFraction: root.Window.height < 560
            ? 0.42 : 0.54
        readonly property real boundedHeight: Math.min(
            440, Math.max(80, root.Window.height * contextFraction))
        Layout.preferredHeight: boundedHeight
        Layout.minimumHeight: Math.min(80, boundedHeight)
        Layout.maximumHeight: boundedHeight
        contentWidth: availableWidth

        ColumnLayout {
            id: albumContextColumn
            width: albumContextScroll.availableWidth
            spacing: MichiThemeState.contentGap

            // ── Album identity / primary action ────────────────────────
            MichiGlassSurface {
                id: albumHeroSurface
                objectName: "albumHeroSurface"
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredHeight: heroContent.implicitHeight
                    + albumHeroSurface.heroPadding * 2
                elevation: "elevated"
                contentPadding: albumHeroSurface.heroPadding
                accented: true
                accentLineVisible: true
                accentColor: paletteBinding.value.accentSafe
                    || MichiPalette.auroraBlue
                textured: true
                materialRole: MichiMaterialRole.hero
                glintMode: "michi"
                readonly property int heroPadding:
                    root.width < MichiBreakpoints.mediumMin
                        ? MichiSpacing.md : MichiSpacing.lg

                /* Do not insert another full-card Rectangle here. Children
                 * of MichiGlassSurface are hosted inside contentPadding, so
                 * such a rectangle becomes an inset card-within-card. The
                 * canonical hero material + artwork-derived accent owns the
                 * surface; artwork remains the contextual colour source. */
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
                            Math.max(128, root.width * 0.15))
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

                        // Canonical facts-only quality projection. Never parse
                        // it to drive behavior or classification. EXACT labels
                        // carry codec/rate/depth or bitrate; MIXED is explicit;
                        // PARTIAL/UNKNOWN stay empty rather than fabricating.
                        MichiText {
                            Layout.fillWidth: true
                            Layout.topMargin: MichiSpacing.xs
                            text: root.technicalSummaryText
                            role: "technical"
                            technical: true
                            color: MichiPalette.textSecondary
                            visible: text.length > 0
                            elide: Text.ElideRight
                        }

                        // Wide owns these facts in the metric rail. Compact
                        // and medium retain them here instead of silently
                        // dropping track count/duration.
                        MichiText {
                            Layout.fillWidth: true
                            text: root.compactAlbumSummary
                            role: "secondary"
                            color: MichiPalette.textMuted
                            visible: !root.showMetricRail && text.length > 0
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
                                    // LibraryContentHost always composes A1,
                                    // the productive consumer for these
                                    // Bridge intents. Menu defaults remain
                                    // fail-closed everywhere else.
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

            // ── Factual knowledge / Library Enrichment ─────────────────
            RowLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: MichiSpacing.md

                MichiText {
                    text: qsTr("Album information")
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
                title: qsTr("Album information")
                showTitle: false
                knowledge: enrichment.albumKnowledge
                // Never render stale knowledge while another entity kind is
                // still active during a navigation transition.
                hasKnowledge: enrichment.activeKind === "album"
                    && enrichment.albumHasKnowledge
                sources: enrichment.albumAttributions
                materialRole: MichiMaterialRole.editorial
                elevation: "subtle"
                shadowed: false
                // The card owns an internal lg inset; zero surface padding
                // avoids the historical double inset on this host.
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

            // At compact widths the inspector joins the bounded context
            // scroller instead of stealing height from the track viewport.
            InspectorPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 160 : 0
                Layout.maximumHeight: 160
                visible: root.inspectedTrack !== null
                    && !MichiBreakpoints.atLeastMedium(root.width)
                title: root.inspectedTrack
                    ? root.inspectedTrack.title : qsTr("Track information")
                rows: root.inspectorRows
                onCloseRequested: {
                    root.inspectedTrack = null
                    root.inspectedIndex = -1
                }
            }
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
        Layout.minimumHeight: Math.min(132,
            Math.max(88, root.Window.height * 0.20))
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
                // Album identity/artwork are already authoritative above.
                // Repeating covers in every row wastes width and competes
                // with technical columns.
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

                // Canonical TrackId-first action seams remain untouched.
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
            title: root.inspectedTrack
                ? root.inspectedTrack.title : qsTr("Track information")
            rows: root.inspectorRows
            onCloseRequested: {
                root.inspectedTrack = null
                root.inspectedIndex = -1
            }
        }
    }

    /* Manual review remains the existing productive enrichment seam. */
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
