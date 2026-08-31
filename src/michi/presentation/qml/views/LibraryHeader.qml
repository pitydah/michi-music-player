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
    property var viewPreferences: ({})

    signal albumModeRequested(string mode)
    signal albumSortRequested(string mode)
    signal albumSortDirectionRequested(bool descending)
    signal albumFilterRequested(string mode)
    signal albumTimelineGroupingRequested(string mode)
    signal albumZoomRequested(real value)
    signal viewPreferenceRequested(string section, string key, var value)
    signal resetViewRequested(string section)

    readonly property bool albumViewsVisible: currentTab === "albums"
        && (typeof library === "undefined" || !library || library.selectedAlbumKey === "")
    readonly property var albumViewModes: [
        { value: "grid", label: qsTr("Gallery"), icon: "view-grid" },
        { value: "cover", label: qsTr("Album Flow"), icon: "view-path" },
        { value: "vinyl", label: qsTr("Listening Wall"), icon: "view-vinyl" },
        { value: "timeline", label: qsTr("Chronology"), icon: "view-timeline" },
        { value: "magazine", label: qsTr("Editorial"), icon: "view-magazine" },
        { value: "list", label: qsTr("Studio List"), icon: "view-list" }
    ]

    readonly property bool hasNonDefaultOptions: MichiThemeState.density !== "standard"
        || MichiThemeState.precisionMode
        || (root.currentTab === "albums" && (
            root.activeViewCustomized()
            || root.albumSortMode !== "title"
            || root.albumSortDescending === true
            || root.albumFilterMode !== "all"
            || root.albumTimelineGrouping !== "decade"
        ))

    function activeViewCustomized() {
        var p = root.viewPreferences
        if (!p)
            return false
        if (root.albumMode === "grid" && p.gallery)
            return p.gallery.artworkSize !== "medium"
                || p.gallery.spacing !== "balanced"
                || p.gallery.metadataLevel !== "standard"
                || p.gallery.precisionMetadata || !p.gallery.quickActions
                || !p.gallery.inspector
        if (root.albumMode === "cover" && p.flow)
            return p.flow.coverSize !== "standard"
                || p.flow.visibleAlbums !== "auto"
                || p.flow.depth !== "standard" || !p.flow.ambientColor
                || p.flow.metadataLevel !== "standard"
        if (root.albumMode === "vinyl" && p.vinyl)
            return p.vinyl.sleeveSize !== "standard"
                || p.vinyl.spacing !== "standard"
                || p.vinyl.reveal !== "standard"
                || p.vinyl.metadataLevel !== "standard"
                || !p.vinyl.artworkLabel || !p.vinyl.inspector
        if (root.albumMode === "timeline" && p.chronology)
            return p.chronology.grouping !== "decade"
                || p.chronology.direction !== "newest"
                || p.chronology.density !== "standard"
                || p.chronology.metadataLevel !== "standard"
                || p.chronology.showPeriodDensity
        if (root.albumMode === "magazine" && p.editorial)
            return !p.editorial.heroVisible
                || p.editorial.informationRichness !== "standard"
                || !p.editorial.cachedEnrichmentVisible
                || p.editorial.archiveLayout !== "list"
        if (root.albumMode === "list" && p.studioList)
            return p.studioList.density !== "standard"
                || p.studioList.artworkSize !== "small"
                || p.studioList.metadataLevel !== "standard"
                || !p.studioList.precisionMetadata || !p.studioList.inspector
                || !p.studioList.artistColumn || !p.studioList.yearColumn
                || !p.studioList.tracksColumn || !p.studioList.durationColumn
                || !p.studioList.formatColumn
        return false
    }

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

    function albumModeLabel() {
        for (var i = 0; i < root.albumViewModes.length; ++i) {
            if (root.albumViewModes[i].value === root.albumMode)
                return root.albumViewModes[i].label
        }
        return qsTr("Gallery")
    }

    function contextualSubtitle() {
        if (typeof library === "undefined" || !library)
            return qsTr("Your local music collection")
        if (library.searchActive) {
            if (root.currentTab === "albums")
                return qsTr("%1 albums matching “%2”")
                    .arg(library.searchAlbumCount).arg(library.searchQuery)
            return qsTr("%1 results matching “%2”")
                .arg(library.searchTotalCount).arg(library.searchQuery)
        }
        if (library.fileCount > 0)
            return qsTr("%1 tracks · %2 albums · %3 artists")
                .arg(library.fileCount).arg(library.albumCount).arg(library.artistCount)
        return qsTr("Your local music collection")
    }

    title: root.tabTitle()
    subtitle: root.contextualSubtitle()

    MichiText {
        visible: root.albumViewsVisible && root.width >= 1120
        text: qsTr("VIEWS")
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
        Accessible.name: qsTr("Album view")
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
            iconName: "view-options"
            accessibleName: root.albumViewsVisible
                ? qsTr("%1 options%2").arg(root.albumModeLabel())
                    .arg(root.hasNonDefaultOptions ? qsTr(" · Customized") : "")
                : qsTr("View options")
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
            viewPreferences: root.viewPreferences
            onAlbumSortRequested: mode => root.albumSortRequested(mode)
            onAlbumSortDirectionRequested: desc => root.albumSortDirectionRequested(desc)
            onAlbumFilterRequested: mode => root.albumFilterRequested(mode)
            onAlbumTimelineGroupingRequested: grp => root.albumTimelineGroupingRequested(grp)
            onAlbumZoomRequested: zoom => root.albumZoomRequested(zoom)
            onViewPreferenceRequested: (section, key, value) =>
                root.viewPreferenceRequested(section, key, value)
            onResetViewRequested: section => root.resetViewRequested(section)
        }
    }
}
