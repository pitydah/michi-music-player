import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root

    property string currentTab: "songs"
    readonly property real defaultSearchWidth: width >= 1480 ? 480 : 420
    property real searchPanePreferredWidth: defaultSearchWidth
    signal currentTabRequested(string tab)

    readonly property bool scanning: (typeof library !== "undefined" && library && library.scanActive === true)

    elevation: "subtle"
    tileSeed: 2
    shadowed: true
    textured: true
    accented: root.scanning || ((typeof library !== "undefined" && library) && library.scanStatus === "FAILED")
    accentColor: ((typeof library !== "undefined" && library) && library.scanStatus === "FAILED")
        ? MichiPalette.error : MichiPalette.auroraCyan
    contentPadding: MichiSpacing.md
    implicitHeight: toolbarContent.implicitHeight + MichiSpacing.md * 2

    function searchPlaceholder() {
        if (currentTab === "albums") return "Search albums or album artists…"
        if (currentTab === "artists") return "Search artists…"
        if (currentTab === "genres") return "Search genres…"
        if (currentTab === "playlists") return "Search tracks or playlists…"
        return "Search title, artist, album, genre or composer…"
    }

    function clampSearchWidth(candidate) {
        var minimum = 300
        var maximum = Math.min(560, root.width * 0.46)
        return Math.max(Math.min(minimum, maximum), Math.min(maximum, candidate))
    }

    // Shared scan entry point (toolbar button + empty-library CTA): scans the
    // configured directory or opens the source picker when none is set.
    // M6-EXT-R4 freeze gate §13: "Scan library" scans ALL active+enabled
    // LibrarySources (serialized). With zero sources it opens the Add
    // Music Source surface. currentDir is a deprecated compatibility
    // projection and never drives this workflow.
    function performScan() {
        if (typeof library === "undefined" || !library)
            return
        if (library.hasSources())
            library.scanAllSources()
        else
            folderDialog.open()
    }

    // LEGACY COMPATIBILITY surface: the folder picker adds a source
    // (multi-source authority lives in the source manager).
    FolderDialog {
        id: folderDialog
        objectName: "libraryFolderDialog"
        title: qsTr("Add music source")
        onAccepted: {
            if (typeof library !== "undefined" && library && folderDialog.selectedFolder) {
                var result = library.add_music_source(
                    "Music",
                    folderDialog.selectedFolder.toString().replace("file://", ""))
            }
        }
    }

    ColumnLayout {
        id: toolbarContent
        anchors.fill: parent
        spacing: MichiSpacing.sm

        GridLayout {
            objectName: "libraryNavigationGrid"
            Layout.fillWidth: true
            columns: root.width < 1100 ? 2 : 4
            // Desktop Tabs → handle → Search totals 8 + 10 + 8 = 26 px:
            // compact perceptual separation without shrinking the hitbox.
            columnSpacing: MichiSpacing.sm
            rowSpacing: MichiSpacing.sm

            LibraryTabs {
                id: libraryNavigation
                Layout.fillWidth: true
                Layout.row: 0
                Layout.column: 0
                Layout.columnSpan: root.width < 1100 ? 2 : 1
                Layout.minimumWidth: Math.min(300, root.width)
                Layout.preferredHeight: MichiMetrics.controlLarge
                currentTab: root.currentTab
                onTabRequested: tab => root.currentTabRequested(tab)
            }

                Item {
                    id: searchResizeHandle
                    objectName: "librarySearchResizeHandle"
                    Layout.row: 0
                    Layout.column: 1
                    Layout.preferredWidth: visible ? 10 : 0
                    Layout.preferredHeight: MichiMetrics.controlLarge
                    visible: root.width >= 1100
                    activeFocusOnTab: visible
                    Accessible.role: Accessible.Slider
                    Accessible.name: qsTr("Resize library search")
                    Accessible.description: qsTr("Use Left and Right arrows; double-click to reset")

                    property real widthAtDragStart: root.searchPanePreferredWidth

                    Rectangle {
                        anchors.centerIn: parent
                        width: 1
                        height: MichiMetrics.iconMedium - MichiSpacing.xxs
                        color: resizeHover.hovered || parent.activeFocus
                            ? MichiSemanticColors.borderStrong
                            : MichiSemanticColors.borderSubtle
                    }
                    HoverHandler {
                        id: resizeHover
                        cursorShape: Qt.SplitHCursor
                    }
                    DragHandler {
                        id: searchResizeDrag
                        target: null
                        xAxis.enabled: true
                        yAxis.enabled: false
                        onActiveChanged: {
                            if (active)
                                searchResizeHandle.widthAtDragStart = root.searchPanePreferredWidth
                        }
                        onActiveTranslationChanged: {
                            root.searchPanePreferredWidth = root.clampSearchWidth(
                                searchResizeHandle.widthAtDragStart - activeTranslation.x)
                        }
                    }
                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        onDoubleTapped: root.searchPanePreferredWidth = root.defaultSearchWidth
                    }
                    Keys.onLeftPressed: root.searchPanePreferredWidth =
                        root.clampSearchWidth(root.searchPanePreferredWidth + 16)
                    Keys.onRightPressed: root.searchPanePreferredWidth =
                        root.clampSearchWidth(root.searchPanePreferredWidth - 16)
                    MichiFocusRing {
                        visualFocus: searchResizeHandle.activeFocus
                            && MichiAccessibility.keyboardMode
                    }
                }

                Item {
                    id: searchPane
                    objectName: "resizableLibrarySearchPane"
                    Layout.row: root.width < 1100 ? 1 : 0
                    Layout.column: root.width < 1100 ? 0 : 2
                    Layout.fillWidth: true
                    Layout.preferredWidth: root.width < 1100
                        ? -1 : root.clampSearchWidth(root.searchPanePreferredWidth)
                    Layout.minimumWidth: Math.min(root.width, 300)
                    Layout.maximumWidth: root.width < 1100 ? root.width : 560
                    Layout.preferredHeight: MichiMetrics.controlLarge

                    RowLayout {
                        anchors.fill: parent
                        spacing: MichiSpacing.sm

                        MichiStatusChip {
                            objectName: "searchNoResultsText"
                            visible: typeof library !== "undefined" && library
                                && library.searchActive
                                && library.searchTotalCount === 0
                            text: qsTr("No results")
                            tone: "warning"
                        }

                        MichiStatusChip {
                            visible: typeof library !== "undefined" && library
                                && library.searchActive
                                && library.searchTotalCount > 0
                            text: qsTr("%1 results").arg(
                                typeof library !== "undefined" && library
                                    ? library.searchTotalCount : 0)
                            tone: "active"
                        }

                        MichiSearchField {
                            id: searchInput
                            Layout.fillWidth: true
                            Layout.minimumWidth: 210
                            text: typeof library !== "undefined" && library ? library.searchQuery : ""
                            placeholderText: root.searchPlaceholder()
                            onEdited: query => { if (typeof library !== "undefined" && library) library.search(query) }
                            onClearRequested: { if (typeof library !== "undefined" && library) library.clear_search() }
                        }
                    }
                }

                MichiSplitButton {
                    id: scanButton
                    objectName: "libraryScanSplitButton"
                    Layout.row: root.width < 1100 ? 1 : 0
                    Layout.column: root.width < 1100 ? 1 : 3
                    Layout.preferredHeight: MichiMetrics.controlMedium
                    Layout.alignment: Qt.AlignVCenter
                    text: root.width < 760 ? qsTr("Scan") : qsTr("Scan library")
                    iconName: ""
                    secondaryIconName: "chevron-down"
                    iconOnly: false
                    accessibleName: qsTr("Scan library")
                    secondaryAccessibleName: qsTr("Music source options")
                    enabled: !root.scanning
                        && typeof library !== "undefined" && library
                    onPrimaryClicked: root.performScan()
                    onSecondaryClicked: sourceMenu.popup()
        // M6-EXT-R4 freeze gate §36: lazy Music Sources manager (heavy
        // dialog stays uninstantiated until opened).
        Loader {
            id: sourcesDialogLoader
            active: false
            sourceComponent: MusicSourcesDialog {
                library: typeof library !== "undefined" ? library : null
                onClosed: sourcesDialogLoader.active = false
            }
        }
        function openSourcesDialog() {
            sourcesDialogLoader.active = true
            sourcesDialogLoader.item.open()
        }

                    MichiMenu {
                        id: sourceMenu
                        x: Math.max(0, parent.width - width)
                        y: parent.height + MichiSpacing.xs

                        Item {
                            implicitWidth: 284
                            implicitHeight: 56
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: MichiSpacing.sm
                                spacing: MichiSpacing.xxs
                                MichiText {
                                    text: qsTr("Music sources")
                                    role: "caption"
                                    color: MichiPalette.textSecondary
                                }
                                MichiText {
                                    Layout.fillWidth: true
                                    text: typeof library !== "undefined" && library
                                        && library.currentDir.length > 0
                                        ? library.currentDir : qsTr("No folder selected")
                                    role: "caption"
                                    elide: Text.ElideMiddle
                                }
                            }
                        }
                        MichiSeparator { }
                        MichiMenuItem {
                            text: qsTr("Music sources…")
                            icon.name: "library"
                            onTriggered: root.openSourcesDialog()
                        }
                    }
            }
        }

        // Transient thin progress row during active scan
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            visible: root.scanning || (typeof library !== "undefined" && library && (library.scanStatus === "FAILED" || library.scanStatus === "CANCELLED"))

            MichiStatusChip {
                objectName: "scanStatusText"
                text: typeof library !== "undefined" && library ? library.scanStatus : ""
                tone: (typeof library !== "undefined" && library && library.scanStatus === "FAILED") ? "error"
                    : (typeof library !== "undefined" && library && library.scanStatus === "COMPLETED") ? "success" : "active"
            }
            MichiText {
                text: typeof library !== "undefined" && library ? (library.scanProcessed + " / " + library.scanTotal) : ""
                role: "technical"
                technical: true
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 6
                radius: 3
                color: MichiPalette.smokeRaised
                visible: typeof library !== "undefined" && library && library.scanTotal > 0
                clip: true
                Rectangle {
                    width: typeof library !== "undefined" && library ? (parent.width * library.scanProgress) : 0
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
                text: typeof library !== "undefined" && library ? library.scanCurrentPath : ""
                Layout.maximumWidth: 220
                role: "caption"
                color: MichiPalette.textMuted
                elide: Text.ElideMiddle
            }
            MichiButton {
                text: qsTr("Cancel")
                variant: "ghost"
                visible: root.scanning
                onClicked: { if (typeof library !== "undefined" && library) library.cancel_scan() }
            }
        }
    }
}
