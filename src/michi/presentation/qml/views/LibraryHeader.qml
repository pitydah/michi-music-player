import QtQuick
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

PageHeader {
    id: root

    property string currentTab: "songs"
    property string albumMode: "grid"
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0

    signal albumModeRequested(string mode)
    signal albumSortRequested(string mode)
    signal albumSortDirectionRequested(bool descending)
    signal albumFilterRequested(string mode)
    signal albumTimelineGroupingRequested(string mode)
    signal albumZoomRequested(real value)

    readonly property bool albumViewsVisible: currentTab === "albums"
        && (typeof library === "undefined" || !library || library.selectedAlbumKey === "")
    readonly property var albumViewModes: [
        { value: "grid", label: "Grid", icon: "view-grid" },
        { value: "cover", label: "PathView", icon: "view-path" },
        { value: "vinyl", label: "Vinyl Wall", icon: "view-vinyl" },
        { value: "timeline", label: "Timeline", icon: "view-timeline" },
        { value: "magazine", label: "Magazine", icon: "view-magazine" },
        { value: "list", label: "List", icon: "view-list" }
    ]

    readonly property bool hasNonDefaultOptions: MichiThemeState.density !== "standard"
        || MichiThemeState.precisionMode
        || (root.currentTab === "albums" && (
            root.albumZoom !== 1.0
            || root.albumSortMode !== "title"
            || root.albumSortDescending === true
            || root.albumFilterMode !== "all"
            || root.albumTimelineGrouping !== "decade"
        ))

    // Wayfinding: the header names the active tab (was a static "Library")
    // so users always know where they are inside the library.
    function tabTitle() {
        switch (root.currentTab) {
            case "albums": return "Albums"
            case "artists": return "Artists"
            case "genres": return "Genres"
            case "playlists": return "Playlists"
            case "favorites": return "Favorites"
            case "history": return "History"
            case "recently": return "Recently Added"
            case "folders": return "Folders"
            default: return "Songs"
        }
    }

    title: root.tabTitle()
    subtitle: (typeof library !== "undefined" && library && library.fileCount > 0)
        ? library.fileCount + " tracks · " + library.albumCount + " albums · "
            + library.artistCount + " artists"
        : "Your local music collection"

    MichiText {
        visible: root.albumViewsVisible && root.width >= 1120
        text: "VIEWS"
        role: "technical"
        technical: true
        color: MichiPalette.textMuted
    }

    MichiSegmentedControl {
        objectName: "albumViewSwitcher"
        visible: root.albumViewsVisible
        model: root.albumViewModes
        currentValue: root.albumMode
        compact: true
        accessiblePrefix: "Album view"
        Accessible.name: "Album view"
        onSelected: value => root.albumModeRequested(value)
    }

    Rectangle {
        visible: root.albumViewsVisible && root.width >= 840
        Layout.preferredWidth: 1
        Layout.preferredHeight: 26
        color: MichiSemanticColors.borderSubtle
    }

    Item {
        id: viewOptionsContainer
        Layout.preferredWidth: 36
        Layout.preferredHeight: 36

        MichiIconButton {
            id: viewOptionsBtn
            anchors.centerIn: parent
            width: MichiMetrics.controlMedium
            height: MichiMetrics.controlMedium
            iconName: "sliders"
            accessibleName: "View options"
            selected: viewOptionsPopup.visible || root.hasNonDefaultOptions
            onClicked: {
                if (viewOptionsPopup.visible) {
                    viewOptionsPopup.close()
                } else {
                    viewOptionsPopup.open()
                }
            }
        }

        // Tiny Aurora status dot for non-default settings
        Rectangle {
            visible: root.hasNonDefaultOptions
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 3
            anchors.rightMargin: 3
            width: 6
            height: 6
            radius: 3
            color: MichiPalette.auroraCyan
        }

        LibraryViewOptionsPopup {
            id: viewOptionsPopup
            x: -244
            y: parent.height + MichiSpacing.xs
            currentTab: root.currentTab
            albumMode: root.albumMode
            albumSortMode: root.albumSortMode
            albumSortDescending: root.albumSortDescending
            albumFilterMode: root.albumFilterMode
            albumTimelineGrouping: root.albumTimelineGrouping
            albumZoom: root.albumZoom
            onAlbumSortRequested: mode => root.albumSortRequested(mode)
            onAlbumSortDirectionRequested: desc => root.albumSortDirectionRequested(desc)
            onAlbumFilterRequested: mode => root.albumFilterRequested(mode)
            onAlbumTimelineGroupingRequested: grp => root.albumTimelineGroupingRequested(grp)
            onAlbumZoomRequested: zoom => root.albumZoomRequested(zoom)
        }
    }
}
