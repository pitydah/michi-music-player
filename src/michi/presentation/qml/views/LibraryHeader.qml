import QtQuick
import QtQuick.Controls.Basic
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
            case "albums": return qsTr("Albums")
            case "artists": return qsTr("Artists")
            case "genres": return qsTr("Genres")
            case "playlists": return qsTr("Playlists")
            case "favorites": return qsTr("Favorites")
            case "history": return qsTr("History")
            case "recently": return qsTr("Recently Added")

            default: return qsTr("Songs")
        }
    }

    function albumModeLabel() {
        for (var i = 0; i < root.albumViewModes.length; ++i) {
            if (root.albumViewModes[i].value === root.albumMode)
                return root.albumViewModes[i].label
        }
        return qsTr("Gallery")
    }

    function albumModeIcon() {
        for (var i = 0; i < root.albumViewModes.length; ++i) {
            if (root.albumViewModes[i].value === root.albumMode)
                return root.albumViewModes[i].icon
        }
        return "view-grid"
    }

    function contextualSubtitle() {
        if (typeof library === "undefined" || !library)
            return qsTr("Your local music collection")
        if (library.searchActive) {
            // LIB-A §51: subtítulo con conteo SCOPED del tab activo —
            // nunca mezclar conteos heterogéneos.
            switch (root.currentTab) {
            case "albums":
                return qsTr("%1 albums matching “%2”")
                    .arg(library.searchAlbumCount).arg(library.searchQuery)
            case "artists":
                return qsTr("%1 artists matching “%2”")
                    .arg(library.searchArtistCount).arg(library.searchQuery)
            case "genres":
                return qsTr("%1 genres matching “%2”")
                    .arg(library.searchGenreCount).arg(library.searchQuery)
            case "favorites":
                return qsTr("%1 favorites matching “%2”")
                    .arg((library.favoriteTrackRows || []).length)
                    .arg(library.searchQuery)
            case "history":
                return qsTr("%1 history items matching “%2”")
                    .arg((library.historyTrackRows || []).length)
                    .arg(library.searchQuery)
            case "recently":
                return qsTr("%1 recently added tracks matching “%2”")
                    .arg((library.recentlyAddedTrackRows || []).length)
                    .arg(library.searchQuery)
            default:
                return qsTr("%1 songs matching “%2”")
                    .arg(library.searchTrackCount).arg(library.searchQuery)
            }
        }
        // LIB-A §35: scope-correct counts — nunca mezclar proyecciones
        // filtradas con totales sin etiquetas.
        if (library.genreFilterActive)
            return qsTr("%1 tracks in %2")
                .arg(library.fileCount).arg(library.selectedGenreName)
        if (root.albumFilterMode !== "all")
            return qsTr("%1 of %2 albums")
                .arg(library.searchAlbumCount
                     || library.filteredAlbumCount).arg(library.albumCount)
        if (library.libraryTrackCount > 0)
            return qsTr("%1 tracks · %2 albums · %3 artists")
                .arg(library.libraryTrackCount).arg(library.albumCount).arg(library.artistCount)
        return qsTr("Your local music collection")
    }

    title: root.tabTitle()
    subtitle: root.contextualSubtitle()

    MichiText {
        visible: root.albumViewsVisible && MichiBreakpoints.isXl(root.width)
        text: qsTr("VIEWS")
        role: "technical"
        technical: true
        color: MichiPalette.textMuted
    }

    MichiSegmentedControl {
        objectName: "albumViewSwitcher"
        visible: root.albumViewsVisible
            && MichiBreakpoints.atLeastMedium(root.width)
        model: root.albumViewModes
        currentValue: root.albumMode
        compact: !MichiBreakpoints.isXl(root.width)
        accessiblePrefix: "Album view"
        Accessible.name: qsTr("Album view")
        onSelected: value => root.albumModeRequested(value)
    }

    Item {
        id: compactPickerHost
        objectName: "compactAlbumViewPicker"
        visible: root.albumViewsVisible
            && !MichiBreakpoints.atLeastMedium(root.width)
        Layout.preferredWidth: 154
        Layout.preferredHeight: MichiMetrics.controlMedium

        MichiButton {
            anchors.fill: parent
            text: root.albumModeLabel()
            iconName: root.albumModeIcon()
            variant: "secondary"
            accessibleName: qsTr("Choose album view. Current: %1")
                .arg(root.albumModeLabel())
            onClicked: compactPicker.visible
                ? compactPicker.close() : compactPicker.open()
        }

        Popup {
            id: compactPicker
            objectName: "compactAlbumViewPopup"
            x: Math.min(0, compactPickerHost.width - implicitWidth)
            y: compactPickerHost.height + MichiSpacing.xs
            padding: MichiSpacing.sm
            modal: false
            focus: true
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
            background: MichiGlassSurface {
                materialRole: MichiMaterialRole.modal
                elevation: "modal"
                contentPadding: 0
                glintMode: "edge"
            }
            contentItem: GridLayout {
                columns: 2
                rowSpacing: MichiSpacing.xs
                columnSpacing: MichiSpacing.xs
                Repeater {
                    model: root.albumViewModes
                    delegate: MichiButton {
                        required property var modelData
                        Layout.preferredWidth: 142
                        text: modelData.label
                        iconName: modelData.icon
                        selected: root.albumMode === modelData.value
                        variant: "ghost"
                        onClicked: {
                            root.albumModeRequested(modelData.value)
                            compactPicker.close()
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        visible: root.albumViewsVisible
            && MichiBreakpoints.atLeastMedium(root.width)
        Layout.preferredWidth: 1
        Layout.preferredHeight: 26
        color: MichiSemanticColors.borderSubtle
    }

    Item {
        id: viewOptionsContainer
        visible: root.albumViewsVisible
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
