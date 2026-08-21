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
    property real albumZoom: 1.0
    property bool sourceExpanded: library.fileCount === 0
    signal currentTabRequested(string tab)
    signal albumSortRequested(string mode)
    signal albumSortDirectionRequested(bool descending)
    signal albumFilterRequested(string mode)
    signal albumTimelineGroupingRequested(string mode)
    signal albumZoomRequested(real value)

    readonly property bool scanning: library.scanStatus !== ""
        && library.scanStatus !== "IDLE"
        && library.scanStatus !== "COMPLETED"
        && library.scanStatus !== "CANCELLED"
        && library.scanStatus !== "FAILED"
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

    function zoomLabel() {
        return Math.round(albumZoom * 100) + "%"
    }

    ColumnLayout {
        id: toolbarContent
        anchors.fill: parent
        spacing: MichiSpacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            LibraryTabs {
                id: libraryNavigation
                Layout.fillWidth: true
                Layout.minimumWidth: 300
                Layout.preferredHeight: MichiMetrics.controlMedium
                currentTab: root.currentTab
                onTabRequested: tab => root.currentTabRequested(tab)
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

            MichiSearchField {
                id: searchInput
                Layout.minimumWidth: 260
                Layout.preferredWidth: root.width >= 1480 ? 440
                    : root.width >= 1120 ? 360 : 280
                Layout.maximumWidth: 460
                text: library.searchQuery
                placeholderText: root.searchPlaceholder()
                onEdited: query => library.search(query)
                onClearRequested: library.clear_search()
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
            visible: root.currentTab === "albums"
                && library.selectedAlbumKey === ""

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

            Item { Layout.fillWidth: true }

            MichiGlassSurface {
                id: albumSizeSurface
                objectName: "albumSizeControl"
                visible: ["grid", "cover", "vinyl"].indexOf(root.albumMode) !== -1
                Layout.preferredWidth: albumSizeRow.implicitWidth + MichiSpacing.sm
                Layout.preferredHeight: 38
                elevation: "subtle"
                contentPadding: MichiSpacing.xxs
                textured: true
                accented: root.albumZoom !== 1.0
                accentColor: MichiPalette.auroraCyan

                RowLayout {
                    id: albumSizeRow
                    anchors.fill: parent
                    spacing: 0
                    MichiIconButton {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        iconName: "zoom-out"
                        accessibleName: "Make album artwork smaller"
                        enabled: root.albumZoom > 0.83
                        onClicked: root.albumZoomRequested(
                            root.albumZoom > 1.01 ? 1.0 : 0.82)
                    }
                    MichiText {
                        Layout.preferredWidth: 42
                        text: root.zoomLabel()
                        role: "technical"
                        technical: true
                        color: root.albumZoom === 1.0
                            ? MichiPalette.textMuted : MichiPalette.auroraCyan
                        horizontalAlignment: Text.AlignHCenter
                    }
                    MichiIconButton {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        iconName: "zoom-in"
                        accessibleName: "Make album artwork larger"
                        enabled: root.albumZoom < 1.21
                        onClicked: root.albumZoomRequested(
                            root.albumZoom < 0.99 ? 1.0 : 1.22)
                    }
                }
            }

            MichiGlassSurface {
                id: organizationSurface
                objectName: "albumOrganizationControl"
                Layout.preferredWidth: organizationRow.implicitWidth + MichiSpacing.xs
                Layout.preferredHeight: 38
                elevation: "subtle"
                contentPadding: MichiSpacing.xxs
                textured: true
                accented: root.albumFilterMode !== "all"
                accentColor: MichiPalette.auroraPurple

                RowLayout {
                    id: organizationRow
                    anchors.fill: parent
                    spacing: 0
                    MichiButton {
                        id: sortButton
                        visible: root.albumMode !== "timeline"
                        Layout.preferredHeight: 32
                        text: root.sortLabel()
                        iconName: "sort"
                        iconOnly: root.width < 1080
                        accessibleName: "Sort albums by " + root.sortLabel()
                        variant: "ghost"
                        onClicked: sortMenu.open()
                    }
                    MichiIconButton {
                        visible: root.albumMode !== "timeline"
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        iconName: root.albumSortDescending
                            ? "sort-descending" : "sort-ascending"
                        accessibleName: root.albumSortDescending
                            ? "Sort descending" : "Sort ascending"
                        selected: root.albumSortDescending
                        onClicked: root.albumSortDirectionRequested(!root.albumSortDescending)
                    }
                    Rectangle {
                        visible: root.albumMode !== "timeline"
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 20
                        color: MichiSemanticColors.borderSubtle
                    }
                    MichiButton {
                        id: filterButton
                        Layout.preferredHeight: 32
                        text: root.filterLabel()
                        iconName: "filter"
                        iconOnly: root.width < 1180
                        accessibleName: "Filter albums: " + root.filterLabel()
                        selected: root.albumFilterMode !== "all"
                        variant: "ghost"
                        onClicked: filterMenu.open()
                    }
                }
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
