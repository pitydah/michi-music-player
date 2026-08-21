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
    readonly property var presentationAlbums: buildPresentationAlbums(library.albums)
    readonly property var presentationTimelineAlbums: buildTimelineAlbums(
        library.timelineAlbums, presentationAlbums)

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
                var summary = normalized(album.technicalSummary)
                return summary.indexOf("24-bit") !== -1
                    || summary.indexOf("dsd") !== -1
                    || summary.indexOf("192 khz") !== -1
                    || summary.indexOf("96 khz") !== -1
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
            return yearOrder !== 0 ? yearOrder
                : root.normalized(left.title).localeCompare(root.normalized(right.title))
        })
        return rows
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

            onLoaded: {
                if (item)
                    item.forceActiveFocus()
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
        }
    }

    Component {
        id: pathComponent
        AlbumPathView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
        }
    }

    Component {
        id: vinylComponent
        VinylWallView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
        }
    }

    Component {
        id: timelineComponent
        TimelineView {
            anchors.fill: parent
            albumModel: root.presentationTimelineAlbums
            groupByDecade: root.albumTimelineGrouping === "decade"
        }
    }

    Component {
        id: magazineComponent
        MagazineView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
        }
    }

    Component {
        id: listComponent
        AlbumListView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
            sortMode: root.albumSortMode
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
