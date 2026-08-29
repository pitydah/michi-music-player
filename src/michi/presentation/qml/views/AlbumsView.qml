import QtQuick
import QtQuick.Layouts
import "../patterns"
import "../theme"

ColumnLayout {
    id: root
    objectName: "albumsView"

    property string albumMode: "grid"
    signal addToPlaylistRequested(string trackId)
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0
    signal sortModeRequested(string mode)
    signal sortDirectionRequested(bool descending)
    readonly property var presentationAlbums: library.albums
    readonly property var presentationTimelineAlbums: library.timelineAlbums

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
            albumZoom: root.albumZoom
        }
    }

    Component {
        id: pathComponent
        AlbumPathView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
            albumZoom: root.albumZoom
        }
    }

    Component {
        id: vinylComponent
        VinylWallView {
            anchors.fill: parent
            albumModel: root.presentationAlbums
            albumZoom: root.albumZoom
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
            sortDescending: root.albumSortDescending
            onSortRequested: mode => root.requestAlbumSort(mode)
        }
    }

    AlbumDetailView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.selectedAlbumKey !== ""
        onAddToPlaylistRequested: trackId => root.addToPlaylistRequested(trackId)
    }
}
