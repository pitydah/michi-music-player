import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root

    property string currentTab: "songs"
    property string albumMode: "grid"
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property bool sourceExpanded: library.fileCount === 0
    signal currentTabRequested(string tab)
    signal albumModeRequested(string mode)
    signal albumSortRequested(string mode)
    signal albumSortDirectionRequested(bool descending)
    signal albumFilterRequested(string mode)
    signal albumTimelineGroupingRequested(string mode)

    readonly property bool scanning: library.scanStatus !== ""
        && library.scanStatus !== "IDLE"
        && library.scanStatus !== "COMPLETED"
        && library.scanStatus !== "CANCELLED"
        && library.scanStatus !== "FAILED"
    readonly property var albumViewModes: [
        { value: "grid", label: "Grid", icon: "view-grid" },
        { value: "cover", label: "PathView", icon: "view-path" },
        { value: "vinyl", label: "Vinyl Wall", icon: "view-vinyl" },
        { value: "timeline", label: "Timeline", icon: "view-timeline" },
        { value: "magazine", label: "Magazine", icon: "view-magazine" },
        { value: "list", label: "List", icon: "view-list" }
    ]
    readonly property var availableViewModes: root.currentTab === "albums"
        && library.selectedAlbumKey === "" ? root.albumViewModes : []
    elevation: "subtle"
    shadowed: true
    textured: true
    accented: root.scanning || library.scanStatus === "FAILED"
    accentColor: library.scanStatus === "FAILED"
        ? MichiPalette.error : MichiPalette.auroraCyan
    contentPadding: MichiSpacing.md
    implicitHeight: toolbarContent.implicitHeight + MichiSpacing.md * 2

    function searchPlaceholder() {
        if (currentTab === "albums") return "Search albums or album artists…"
        if (currentTab === "artists") return "Search artists…"
        if (currentTab === "genres") return "Search genres…"
        if (currentTab === "folders") return "Search folders or paths…"
        if (currentTab === "playlists") return "Search tracks or playlists…"
        return "Search title, artist, album, genre or composer…"
    }

    function sortLabel() {
        var labels = {
            title: "Title", artist: "Album artist", year: "Release year",
            tracks: "Track count", duration: "Duration"
        }
        return labels[albumSortMode] || "Title"
    }

    function filterLabel() {
        var labels = {
            all: "All albums", artwork: "With artwork",
            missingArtwork: "Missing artwork", dated: "With year",
            undated: "Unknown year", hires: "Hi-Res"
        }
        return labels[albumFilterMode] || "All albums"
    }

    ColumnLayout {
        id: toolbarContent
        anchors.fill: parent
        spacing: MichiSpacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiSearchField {
                id: searchInput
                Layout.minimumWidth: 280
                Layout.preferredWidth: root.width >= 1480 ? 520
                    : root.width >= 1120 ? 400 : 300
                Layout.maximumWidth: 560
                text: library.searchQuery
                placeholderText: root.searchPlaceholder()
                onEdited: query => library.search(query)
                onClearRequested: library.clear_search()
            }

            MichiStatusChip {
                objectName: "searchNoResultsText"
                visible: library.searchActive && library.searchTotalCount === 0
                text: "No results"
                tone: "warning"
            }

            MichiStatusChip {
                visible: library.searchActive && library.searchTotalCount > 0
                text: library.searchTotalCount + " results"
                tone: "active"
            }

            LibraryTabs {
                id: libraryNavigation
                Layout.fillWidth: true
                Layout.minimumWidth: 220
                Layout.preferredHeight: MichiMetrics.controlMedium
                currentTab: root.currentTab
                onTabRequested: tab => root.currentTabRequested(tab)
            }

            MichiIconButton {
                iconName: "folder"
                selected: root.sourceExpanded
                accessibleName: root.sourceExpanded
                    ? "Hide library source" : "Show library source"
                onClicked: root.sourceExpanded = !root.sourceExpanded
            }

            MichiButton {
                text: root.width < 760 ? "Scan" : "Scan library"
                iconName: "library"
                iconOnly: root.width < 980
                accessibleName: "Scan library"
                enabled: !root.scanning
                    && (dirInput.text.length > 0 || library.currentDir.length > 0)
                onClicked: {
                    var directory = dirInput.text.length > 0
                        ? dirInput.text : library.currentDir
                    library.scan(directory)
                }
            }
        }

        RowLayout {
            id: sourceRow
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            visible: root.sourceExpanded

            MichiIcon {
                iconColor: MichiPalette.textMuted
                name: "folder"
                Layout.preferredWidth: MichiMetrics.iconSmall
                Layout.preferredHeight: MichiMetrics.iconSmall
            }
            MichiText {
                text: "SOURCE"
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            MichiTextField {
                id: dirInput
                Layout.fillWidth: true
                text: library.currentDir
                placeholderText: "Choose a local music directory…"
                accessibleName: "Music directory"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            visible: root.availableViewModes.length > 1

            MichiText {
                text: "ALBUMS"
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
                visible: root.width >= 1040
            }
            MichiStatusChip {
                text: library.albums.length
                    + (library.albums.length === 1 ? " album" : " albums")
                tone: "neutral"
            }

            Rectangle {
                Layout.preferredWidth: 1
                Layout.preferredHeight: 24
                color: MichiSemanticColors.borderSubtle
            }
            MichiText {
                visible: root.width >= 1180
                text: "VIEW"
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            MichiSegmentedControl {
                objectName: "albumViewSwitcher"
                compact: root.width < 1480
                model: root.availableViewModes
                currentValue: root.albumMode
                accessiblePrefix: "Album view"
                Accessible.name: "Album view"
                onSelected: value => root.albumModeRequested(value)
            }

            Item { Layout.fillWidth: true }

            MichiButton {
                id: sortButton
                visible: root.albumMode !== "timeline"
                text: root.sortLabel()
                iconName: "sort"
                iconOnly: root.width < 1080
                accessibleName: "Sort albums by " + root.sortLabel()
                variant: "secondary"
                onClicked: sortMenu.open()
            }
            MichiIconButton {
                visible: root.albumMode !== "timeline"
                iconName: root.albumSortDescending
                    ? "sort-descending" : "sort-ascending"
                accessibleName: root.albumSortDescending
                    ? "Sort descending" : "Sort ascending"
                selected: root.albumSortDescending
                onClicked: root.albumSortDirectionRequested(!root.albumSortDescending)
            }
            MichiSegmentedControl {
                visible: root.albumMode === "timeline"
                compact: root.width < 1080
                model: [
                    { value: "decade", label: "Decades", icon: "view-timeline" },
                    { value: "year", label: "Years", icon: "history" }
                ]
                currentValue: root.albumTimelineGrouping
                accessiblePrefix: "Timeline grouping"
                Accessible.name: "Timeline grouping"
                onSelected: value => root.albumTimelineGroupingRequested(value)
            }
            MichiButton {
                id: filterButton
                text: root.filterLabel()
                iconName: "filter"
                iconOnly: root.width < 1180
                accessibleName: "Filter albums: " + root.filterLabel()
                selected: root.albumFilterMode !== "all"
                variant: "secondary"
                onClicked: filterMenu.open()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            visible: root.scanning || library.scanStatus === "FAILED"
                || library.scanStatus === "CANCELLED"

            MichiStatusChip {
                objectName: "scanStatusText"
                text: library.scanStatus
                tone: library.scanStatus === "FAILED" ? "error"
                    : library.scanStatus === "COMPLETED" ? "success" : "active"
            }
            MichiText {
                text: library.scanProcessed + " / " + library.scanTotal
                role: "technical"
                technical: true
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 6
                radius: 3
                color: MichiPalette.smokeRaised
                visible: library.scanTotal > 0
                clip: true
                Rectangle {
                    width: parent.width * library.scanProgress
                    height: parent.height
                    radius: 3
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: MichiPalette.auroraBlue }
                        GradientStop { position: 1; color: MichiPalette.auroraCyan }
                    }
                    Behavior on width {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation {
                            duration: MichiMotion.standard
                            easing.type: MichiMotion.outCubic
                        }
                    }
                }
            }
            MichiText {
                text: library.scanCurrentPath
                Layout.maximumWidth: 220
                role: "caption"
                color: MichiPalette.textMuted
                elide: Text.ElideMiddle
            }
            MichiButton {
                text: "Cancel"
                variant: "ghost"
                visible: root.scanning
                onClicked: library.cancel_scan()
            }
        }
    }

    MichiMenu {
        id: sortMenu
        x: Math.max(0, sortButton.mapToItem(root, 0, 0).x)
        y: sortButton.mapToItem(root, 0, sortButton.height).y + MichiSpacing.xs
        MenuItem { text: "Title"; onTriggered: root.albumSortRequested("title") }
        MenuItem { text: "Album artist"; onTriggered: root.albumSortRequested("artist") }
        MenuItem { text: "Release year"; onTriggered: root.albumSortRequested("year") }
        MenuItem { text: "Track count"; onTriggered: root.albumSortRequested("tracks") }
        MenuItem { text: "Duration"; onTriggered: root.albumSortRequested("duration") }
    }

    MichiMenu {
        id: filterMenu
        x: Math.max(0, filterButton.mapToItem(root, 0, 0).x)
        y: filterButton.mapToItem(root, 0, filterButton.height).y + MichiSpacing.xs
        MenuItem { text: "All albums"; onTriggered: root.albumFilterRequested("all") }
        MenuItem { text: "With artwork"; onTriggered: root.albumFilterRequested("artwork") }
        MenuItem { text: "Missing artwork"; onTriggered: root.albumFilterRequested("missingArtwork") }
        MenuItem { text: "With release year"; onTriggered: root.albumFilterRequested("dated") }
        MenuItem { text: "Unknown release year"; onTriggered: root.albumFilterRequested("undated") }
        MenuItem { text: "Hi-Res"; onTriggered: root.albumFilterRequested("hires") }
    }
}
