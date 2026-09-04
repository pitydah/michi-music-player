import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import "../patterns"
import "../theme"

ColumnLayout {
    id: root
    objectName: "albumsView"

    property string albumMode: "grid"
    property string addTargetPath: ""
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0
    property var viewPreferences: ({})
    property var browseState: null
    property string loadedMode: "grid"
    property string pendingMode: "grid"
    property bool transitionsReady: false
    signal sortModeRequested(string mode)
    signal sortDirectionRequested(bool descending)
    // LIB-A §36/37: UNA autoridad — library.albums ya es la proyección
    // de la aplicación (filtro semántico + sort del query service). El
    // QML solo aplica estrategias de PRESENTACIÓN del view (cronología
    // del timeline, ranking editorial del magazine).
    readonly property var presentationAlbums: library.albums
    readonly property var presentationTimelineAlbums: buildTimelineAlbums(
        library.timelineAlbums, library.albums)
    readonly property var editorialAlbums: buildEditorialAlbums(presentationAlbums)
    readonly property var currentBrowseAlbum: findAlbumByKey(
        browseState ? browseState.currentKey : "")
    readonly property int enrichmentRevision: typeof libraryEnrichment !== "undefined"
        && libraryEnrichment ? libraryEnrichment.revision : 0
    readonly property var currentBrowseEnrichment: currentBrowseAlbum
        && typeof libraryEnrichment !== "undefined" && libraryEnrichment
        ? libraryEnrichment.album(currentBrowseAlbum.key, enrichmentRevision) : ({
            albumKey: "", hasCachedKnowledge: false, knowledge: ({})
        })

    function findAlbumByKey(key) {
        for (var i = 0; i < presentationAlbums.length; ++i)
            if (presentationAlbums[i].key === key) return presentationAlbums[i]
        return null
    }

    function inspectorEnabled() {
        if (width < MichiBreakpoints.medium)
            return false
        if (albumMode === "grid") return viewPreferences.gallery
            ? viewPreferences.gallery.inspector : true
        if (albumMode === "vinyl") return viewPreferences.vinyl
            ? viewPreferences.vinyl.inspector : true
        if (albumMode === "list") return viewPreferences.studioList
            ? viewPreferences.studioList.inspector : true
        return false
    }

    function normalized(value) {
        return String(value || "").toLocaleLowerCase()
    }

    function buildTimelineAlbums(source, visibleAlbums) {
        var visibleKeys = {}
        for (var i = 0; i < visibleAlbums.length; ++i)
            visibleKeys[visibleAlbums[i].key] = true
        var rows = (source ? source.slice() : []).filter(function(album) {
            return Boolean(visibleKeys[album.key])
        })
        rows.sort(function(left, right) {
            var yearOrder = Number(right.year || 0) - Number(left.year || 0)
            if (root.viewPreferences.chronology
                    && root.viewPreferences.chronology.direction === "oldest")
                yearOrder = -yearOrder
            return yearOrder !== 0 ? yearOrder
                : root.normalized(left.title).localeCompare(root.normalized(right.title))
        })
        return rows
    }

    function buildEditorialAlbums(source) {
        var rows = source ? source.slice() : []
        rows.sort(function(left, right) {
            var recentOrder = Number(Boolean(right.isRecentlyAdded))
                - Number(Boolean(left.isRecentlyAdded))
            if (recentOrder !== 0)
                return recentOrder
            var favoriteOrder = Number(Boolean(right.isFavorite))
                - Number(Boolean(left.isFavorite))
            if (favoriteOrder !== 0)
                return favoriteOrder
            var fidelityOrder = Number(Boolean(right.containsHighResolution))
                - Number(Boolean(left.containsHighResolution))
            if (fidelityOrder !== 0)
                return fidelityOrder
            var artworkOrder = Number(Boolean(right.hasArtwork))
                - Number(Boolean(left.hasArtwork))
            if (artworkOrder !== 0)
                return artworkOrder
            var yearOrder = Number(right.year || 0) - Number(left.year || 0)
            if (yearOrder !== 0)
                return yearOrder
            return root.normalized(left.title).localeCompare(root.normalized(right.title))
        })
        return rows
    }

    // Header click-to-sort entry point: same mode toggles direction.
    function requestAlbumSort(mode) {
        if (mode === root.albumSortMode)
            root.sortDirectionRequested(!root.albumSortDescending)
        else
            root.sortModeRequested(mode)
    }

    function componentForMode(mode) {
        switch (mode) {
            case "cover": return pathComponent
            case "vinyl": return vinylComponent
            case "timeline": return timelineComponent
            case "magazine": return magazineComponent
            case "list": return listComponent
            default: return gridComponent
        }
    }

    onAlbumModeChanged: {
        pendingMode = albumMode
        if (!transitionsReady || MichiAccessibility.reducedMotion
                || root.Window.window === null) {
            if (modeLoader.item)
                modeLoader.item.objectName = ""
            loadedMode = pendingMode
            modeLoader.opacity = 1
            modeLoader.scale = 1
        } else {
            modeEnter.stop()
            modeExit.restart()
        }
    }

    Component.onCompleted: {
        loadedMode = albumMode
        pendingMode = albumMode
        transitionsReady = true
    }

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiTheme.space8

    RowLayout {
        id: modeArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.selectedAlbumKey === "" && root.presentationAlbums.length > 0

        Loader {
            id: modeLoader
            objectName: "albumModeLoader"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Layout.preferredWidth: Math.max(0, modeArea.width
                - (albumInspector.visible ? 320 + modeArea.spacing : 0))
            Layout.fillHeight: true
            active: modeArea.visible
            asynchronous: false
            sourceComponent: root.componentForMode(root.loadedMode)
            opacity: 1
            scale: 1

        }

        NumberAnimation {
            id: modeExit
            target: modeLoader
            property: "opacity"
            to: 0
            duration: MichiMotion.viewExit
            easing.type: MichiMotion.inOutCubic
            onStopped: {
                if (modeLoader.item)
                    modeLoader.item.objectName = ""
                root.loadedMode = root.pendingMode
                modeLoader.scale = 0.985
                Qt.callLater(function() { modeEnter.restart() })
            }
        }
        ParallelAnimation {
            id: modeEnter
            NumberAnimation {
                target: modeLoader
                property: "opacity"
                from: 0
                to: 1
                duration: MichiMotion.viewEnter
                easing.type: MichiMotion.outCubic
            }
            NumberAnimation {
                target: modeLoader
                property: "scale"
                from: 0.985
                to: 1
                duration: MichiMotion.viewEnter
                easing.type: MichiMotion.outCubic
            }
        }

        LibraryAlbumInspector {
            id: albumInspector
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            visible: root.inspectorEnabled() && root.currentBrowseAlbum !== null
            album: root.currentBrowseAlbum
            hasCachedKnowledge: root.currentBrowseEnrichment.hasCachedKnowledge || false
            cachedKnowledge: root.currentBrowseEnrichment.knowledge || ({})
            showCachedContext: root.albumMode === "magazine"
                ? root.viewPreferences.editorial.cachedEnrichmentVisible : true
            onlineEnabled: typeof enrichment !== "undefined" && enrichment
                ? enrichment.onlineEnabled : false
            onOpenRequested: key => library.select_album(key)
            onPlayRequested: key => library.play_album(key)
            onEnrichmentRequested: key => enrichment.activate_album(key)
        }
    }

    EmptyState {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.selectedAlbumKey === ""
            && root.presentationAlbums.length === 0
        title: library.searchActive || root.albumFilterMode !== "all"
            ? "No matching albums" : "No albums yet"
        message: library.searchActive
            ? "Try a different search or clear the current query."
            : root.albumFilterMode !== "all"
                ? "Change or clear the active album filter."
                : "Scan a music folder to build your album library."
        iconName: "library"
    }

    Component {
        id: gridComponent
        AlbumGridView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
            albumZoom: root.albumZoom
            browseState: root.browseState
            spacingMode: root.viewPreferences.gallery
                ? root.viewPreferences.gallery.spacing : "balanced"
            metadataLevel: root.viewPreferences.gallery
                ? root.viewPreferences.gallery.metadataLevel : "standard"
            quickActions: root.viewPreferences.gallery
                ? root.viewPreferences.gallery.quickActions : true
            precisionMetadata: root.viewPreferences.gallery
                ? root.viewPreferences.gallery.precisionMetadata : false
        }
    }

    Component {
        id: pathComponent
        AlbumPathView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
            albumZoom: root.albumZoom
            browseState: root.browseState
            visibleAlbums: root.viewPreferences.flow
                ? root.viewPreferences.flow.visibleAlbums : "auto"
            depthMode: root.viewPreferences.flow
                ? root.viewPreferences.flow.depth : "standard"
            ambientColor: root.viewPreferences.flow
                ? root.viewPreferences.flow.ambientColor : true
            metadataLevel: root.viewPreferences.flow
                ? root.viewPreferences.flow.metadataLevel : "standard"
            cachedKnowledge: root.currentBrowseEnrichment.knowledge || ({})
            hasCachedKnowledge: root.currentBrowseEnrichment.hasCachedKnowledge || false
            cachedAlbumKey: root.currentBrowseEnrichment.albumKey || ""
        }
    }

    Component {
        id: vinylComponent
        VinylWallView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
            albumZoom: root.albumZoom
            browseState: root.browseState
            spacingMode: root.viewPreferences.vinyl
                ? root.viewPreferences.vinyl.spacing : "standard"
            revealMode: root.viewPreferences.vinyl
                ? root.viewPreferences.vinyl.reveal : "standard"
            metadataLevel: root.viewPreferences.vinyl
                ? root.viewPreferences.vinyl.metadataLevel : "standard"
            artworkLabel: root.viewPreferences.vinyl
                ? root.viewPreferences.vinyl.artworkLabel : true
        }
    }

    Component {
        id: timelineComponent
        TimelineView {
            anchors.fill: parent
            albumModel: root.presentationTimelineAlbums
            groupByDecade: root.albumTimelineGrouping === "decade"
            browseState: root.browseState
            direction: root.viewPreferences.chronology
                ? root.viewPreferences.chronology.direction : "newest"
            densityMode: root.viewPreferences.chronology
                ? root.viewPreferences.chronology.density : "standard"
            metadataLevel: root.viewPreferences.chronology
                ? root.viewPreferences.chronology.metadataLevel : "standard"
            showPeriodDensity: root.viewPreferences.chronology
                ? root.viewPreferences.chronology.showPeriodDensity : false
        }
    }

    Component {
        id: magazineComponent
        MagazineView {
            anchors.fill: parent
            albumModel: root.editorialAlbums
            browseState: root.browseState
            heroVisible: root.viewPreferences.editorial
                ? root.viewPreferences.editorial.heroVisible : true
            informationRichness: root.viewPreferences.editorial
                ? root.viewPreferences.editorial.informationRichness : "standard"
            archiveLayout: root.viewPreferences.editorial
                ? root.viewPreferences.editorial.archiveLayout : "list"
            cachedKnowledge: root.currentBrowseEnrichment.knowledge || ({})
            hasCachedKnowledge: root.currentBrowseEnrichment.hasCachedKnowledge || false
            cachedAlbumKey: root.currentBrowseEnrichment.albumKey || ""
            showCachedContext: root.viewPreferences.editorial
                ? root.viewPreferences.editorial.cachedEnrichmentVisible : true
        }
    }

    Component {
        id: listComponent
        AlbumListView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
            browseState: root.browseState
            viewPreferences: root.viewPreferences.studioList || ({})
            sortMode: root.albumSortMode
            sortDescending: root.albumSortDescending
            onSortRequested: mode => root.requestAlbumSort(mode)
        }
    }

    AlbumDetailView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.selectedAlbumKey !== ""
        addTargetPath: root.addTargetPath
        onAddTargetPathChanged: root.addTargetPath = addTargetPath
    }
}
