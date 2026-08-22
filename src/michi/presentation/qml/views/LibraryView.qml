import QtQuick
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property string currentTab: "songs"
    // M6-PRODUCTION-INTEGRATION: albumMode lives HERE (the root survives
    // the tab recreation) — AlbumsView is recreated on every tab switch and
    // must never be the source of a preference we want to preserve.
    property string albumMode: "grid"
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0

    readonly property var albumModes: [
        "grid", "cover", "vinyl", "timeline", "magazine", "list"
    ]

    function requestAlbumMode(mode) {
        if (albumModes.indexOf(mode) !== -1)
            albumMode = mode
    }

    function requestAlbumZoom(value) {
        albumZoom = Math.max(0.82, Math.min(1.22, value))
    }

    function syncEntitySelection() {
        if (library.selectedAlbumKey !== "")
            currentTab = "albums"
        else if (library.selectedArtistKey !== "")
            currentTab = "artists"
    }

    Connections {
        target: library
        function onLibrary_changed() { root.syncEntitySelection() }
    }

    Component.onCompleted: syncEntitySelection()

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiThemeState.contentGap

        LibraryHeader {
            Layout.fillWidth: true
            currentTab: root.currentTab
            albumMode: root.albumMode
            albumSortMode: root.albumSortMode
            albumSortDescending: root.albumSortDescending
            albumFilterMode: root.albumFilterMode
            albumTimelineGrouping: root.albumTimelineGrouping
            albumZoom: root.albumZoom
            onAlbumModeRequested: mode => root.requestAlbumMode(mode)
            onAlbumSortRequested: mode => root.albumSortMode = mode
            onAlbumSortDirectionRequested: descending => root.albumSortDescending = descending
            onAlbumFilterRequested: mode => root.albumFilterMode = mode
            onAlbumTimelineGroupingRequested: mode => root.albumTimelineGrouping = mode
            onAlbumZoomRequested: value => root.requestAlbumZoom(value)
        }

        LibraryToolbar {
            Layout.fillWidth: true
            currentTab: root.currentTab
            onCurrentTabRequested: tab => root.currentTab = tab
        }

        LibraryContentHost {
            currentTab: root.currentTab
            albumMode: root.albumMode
            albumSortMode: root.albumSortMode
            albumSortDescending: root.albumSortDescending
            albumFilterMode: root.albumFilterMode
            albumTimelineGrouping: root.albumTimelineGrouping
            albumZoom: root.albumZoom
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
