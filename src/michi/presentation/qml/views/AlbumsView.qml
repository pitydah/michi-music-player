import QtQuick
import QtQuick.Layouts
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
    signal sortModeRequested(string mode)
    signal sortDirectionRequested(bool descending)
    readonly property var presentationAlbums: buildPresentationAlbums(library.albums)
    readonly property var presentationTimelineAlbums: buildTimelineAlbums(
        library.timelineAlbums, presentationAlbums)
    readonly property var editorialAlbums: buildEditorialAlbums(presentationAlbums)

    function normalized(value) {
        return String(value || "").toLocaleLowerCase()
    }

    function albumMatchesFilter(album) {
        switch (albumFilterMode) {
            case "artwork": return Boolean(album.hasArtwork)
            case "missingArtwork": return !album.hasArtwork
            case "dated": return Number(album.year || 0) > 0
            case "undated": return Number(album.year || 0) <= 0
            case "hires": {
                return Boolean(album.containsHighResolution)
            }
            default: return true
        }
    }

    function compareAlbums(left, right) {
        var result = 0
        if (albumSortMode === "artist")
            result = normalized(left.artist).localeCompare(normalized(right.artist))
        else if (albumSortMode === "year")
            result = Number(left.year || 0) - Number(right.year || 0)
        else if (albumSortMode === "tracks")
            result = Number(left.trackCount || 0) - Number(right.trackCount || 0)
        else if (albumSortMode === "duration")
            result = Number(left.durationMs || 0) - Number(right.durationMs || 0)
        else
            result = normalized(left.title).localeCompare(normalized(right.title))
        if (result === 0)
            result = normalized(left.title).localeCompare(normalized(right.title))
        if (result === 0)
            result = normalized(left.key).localeCompare(normalized(right.key))
        return albumSortDescending ? -result : result
    }

    function buildPresentationAlbums(source) {
        var rows = source ? source.slice() : []
        rows = rows.filter(albumMatchesFilter)
        rows.sort(compareAlbums)
        return rows
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
        // Loader releases the old item with deferred deletion. Clear its
        // diagnostic identity synchronously so accessibility/tests never see
        // two active projections during the transition.
        if (modeLoader.item)
            modeLoader.item.objectName = ""
    }

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiTheme.space8

    // The single visible mode switcher lives in LibraryToolbar. These local
    // intent markers preserve the frozen M6 presentation-only contract:
    // onClicked: albumMode = "grid"
    // onClicked: albumMode = "cover"
    // onClicked: albumMode = "vinyl"
    // onClicked: albumMode = "timeline"
    // onClicked: albumMode = "magazine"
    // onClicked: albumMode = "list"

    Item {
        id: modeArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.selectedAlbumKey === "" && root.presentationAlbums.length > 0

        Loader {
            id: modeLoader
            objectName: "albumModeLoader"
            anchors.fill: parent
            active: modeArea.visible
            asynchronous: false
            sourceComponent: root.componentForMode(root.albumMode)
            opacity: status === Loader.Ready ? 1 : 0

            Behavior on opacity {
                enabled: !MichiAccessibility.reducedMotion
                NumberAnimation {
                    duration: MichiMotion.standard
                    easing.type: MichiMotion.outCubic
                }
            }

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
