import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root

    property string currentTab: "songs"
    property string albumMode: "grid"
    property bool sourceExpanded: library.fileCount === 0
    signal albumModeRequested(string mode)

    readonly property bool scanning: library.scanStatus !== ""
        && library.scanStatus !== "IDLE"
        && library.scanStatus !== "COMPLETED"
        && library.scanStatus !== "CANCELLED"
        && library.scanStatus !== "FAILED"
    readonly property bool precisionRelevant: [
        "songs", "albums", "favorites", "history", "recently", "playlists"
    ].indexOf(currentTab) !== -1

    elevation: "subtle"
    accented: root.scanning || library.scanStatus === "FAILED"
    accentColor: library.scanStatus === "FAILED"
        ? MichiPalette.error : MichiPalette.auroraCyan
    contentPadding: MichiSpacing.md
    implicitHeight: toolbarContent.implicitHeight + MichiSpacing.md * 2

    function tabLabel() {
        var labels = {
            songs: "Songs", albums: "Albums", artists: "Artists",
            genres: "Genres", folders: "Folders", favorites: "Favorites",
            history: "History", recently: "Recently added", playlists: "Playlists"
        }
        return labels[currentTab] || "Library"
    }

    function tabCount() {
        if (currentTab === "songs") return library.songRows.length
        if (currentTab === "albums") return library.albums.length
        if (currentTab === "artists") return library.artists.length
        if (currentTab === "genres") return library.genres.length
        if (currentTab === "folders") return library.folders.length
        if (currentTab === "favorites") return library.favoriteTrackRows.length
        if (currentTab === "history") return library.historyTrackRows.length
        if (currentTab === "recently") return library.recentlyAddedTrackRows.length
        if (currentTab === "playlists") return library.playlists.length
        return 0
    }

    function searchPlaceholder() {
        if (currentTab === "albums") return "Search albums or album artists…"
        if (currentTab === "artists") return "Search artists…"
        if (currentTab === "genres") return "Search genres…"
        if (currentTab === "folders") return "Search folders or paths…"
        if (currentTab === "playlists") return "Search tracks or playlists…"
        return "Search title, artist, album, genre or composer…"
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
                Layout.fillWidth: true
                text: library.searchQuery
                placeholderText: root.searchPlaceholder()
                onEdited: query => library.search(query)
                onClearRequested: library.clear_search()
            }

            MichiStatusChip {
                objectName: "searchNoResultsText"
                visible: library.searchActive
                text: library.searchTotalCount === 0
                    ? "No results" : library.searchTotalCount + " results"
                tone: library.searchTotalCount === 0 ? "warning" : "active"
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
            spacing: MichiSpacing.md

            MichiText {
                text: root.tabLabel()
                role: "secondary"
                font.weight: Font.DemiBold
            }
            MichiStatusChip {
                text: root.tabCount() + (root.tabCount() === 1 ? " item" : " items")
                tone: "neutral"
            }

            Item { Layout.fillWidth: true }

            RowLayout {
                spacing: MichiSpacing.sm
                visible: root.currentTab === "albums"
                    && library.selectedAlbumKey === ""
                MichiText {
                    visible: root.width >= 1080
                    text: "VIEW"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                }
                MichiSegmentedControl {
                    objectName: "albumViewSwitcher"
                    compact: true
                    model: [
                        { value: "grid", label: "Grid", icon: "view-grid" },
                        { value: "cover", label: "PathView", icon: "view-path" },
                        { value: "vinyl", label: "Vinyl Wall", icon: "view-vinyl" },
                        { value: "timeline", label: "Timeline", icon: "view-timeline" },
                        { value: "magazine", label: "Magazine", icon: "view-magazine" },
                        { value: "list", label: "List", icon: "view-list" }
                    ]
                    currentValue: root.albumMode
                    Accessible.name: "Album view"
                    onSelected: value => root.albumModeRequested(value)
                }
            }

            RowLayout {
                spacing: MichiSpacing.sm
                MichiText {
                    visible: root.width >= 1180
                    text: "DENSITY"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                }
                MichiSegmentedControl {
                    model: [
                        { value: "comfortable", label: "Comfortable", icon: "density-comfortable" },
                        { value: "standard", label: "Standard", icon: "density-standard" },
                        { value: "compact", label: "Compact", icon: "density-compact" }
                    ]
                    currentValue: MichiThemeState.density
                    compact: root.width < 1180
                    Accessible.name: "Library density"
                    onSelected: value => MichiThemeState.density = value
                }
            }

            MichiSwitch {
                visible: root.precisionRelevant
                text: root.width < 980 ? "Precision" : "Precision metadata"
                checked: MichiThemeState.precisionMode
                onToggled: MichiThemeState.precisionMode = checked
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            visible: library.scanStatus !== "" && library.scanStatus !== "IDLE"

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
}
