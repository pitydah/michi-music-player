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
    property real searchPanePreferredWidth: width >= 1480 ? 640 : 520
    signal currentTabRequested(string tab)

    readonly property bool scanning: (typeof library !== "undefined" && library)
        && library.scanStatus !== ""
        && library.scanStatus !== "IDLE"
        && library.scanStatus !== "COMPLETED"
        && library.scanStatus !== "CANCELLED"
        && library.scanStatus !== "FAILED"
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
        var minimum = root.width < 980 ? 300 : 430
        var maximum = root.width < 900 ? root.width : 760
        return Math.max(Math.min(minimum, maximum), Math.min(maximum, candidate))
    }

    // Shared scan entry point (toolbar button + empty-library CTA): scans the
    // configured directory or opens the source picker when none is set.
    function performScan() {
        if (typeof library === "undefined" || !library)
            return
        if (library.currentDir.length > 0)
            library.scan(library.currentDir)
        else
            folderDialog.open()
    }

    FolderDialog {
        id: folderDialog
        objectName: "libraryFolderDialog"
        title: qsTr("Choose music folder")
        onAccepted: {
            if (typeof library !== "undefined" && library)
                library.scan_url(selectedFolder)
        }
    }

    ColumnLayout {
        id: toolbarContent
        anchors.fill: parent
        spacing: MichiSpacing.sm

        GridLayout {
            objectName: "libraryNavigationGrid"
            Layout.fillWidth: true
            columns: root.width < 900 ? 1 : 2
            columnSpacing: MichiSpacing.md
            rowSpacing: MichiSpacing.sm

            LibraryTabs {
                id: libraryNavigation
                Layout.fillWidth: true
                Layout.minimumWidth: Math.min(300, root.width)
                Layout.preferredHeight: MichiMetrics.controlLarge
                currentTab: root.currentTab
                onTabRequested: tab => root.currentTabRequested(tab)
            }

            Item {
                id: searchPane
                objectName: "resizableLibrarySearchPane"
                Layout.fillWidth: root.width < 900
                Layout.preferredWidth: root.clampSearchWidth(root.searchPanePreferredWidth)
                Layout.minimumWidth: Math.min(root.width,
                    root.width < 980 ? 300 : 430)
                Layout.maximumWidth: root.width < 900 ? root.width : 760
                Layout.preferredHeight: MichiMetrics.controlLarge

                RowLayout {
                    anchors.fill: parent
                    spacing: MichiSpacing.sm

                    Rectangle {
                        id: searchResizeHandle
                        objectName: "librarySearchResizeHandle"
                        Layout.preferredWidth: visible ? MichiSpacing.sm : 0
                        Layout.fillHeight: true
                        visible: root.width >= 900
                        activeFocusOnTab: visible
                        color: resizeHover.hovered || activeFocus
                            ? MichiSemanticColors.borderStrong
                            : "transparent"
                        Accessible.role: Accessible.Separator
                        Accessible.name: qsTr("Resize library search")

                        property real widthAtDragStart: root.searchPanePreferredWidth

                        HoverHandler {
                            id: resizeHover
                            cursorShape: Qt.SizeHorCursor
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
                        Keys.onLeftPressed: root.searchPanePreferredWidth =
                            root.clampSearchWidth(root.searchPanePreferredWidth + 16)
                        Keys.onRightPressed: root.searchPanePreferredWidth =
                            root.clampSearchWidth(root.searchPanePreferredWidth - 16)
                        MichiFocusRing {
                            visualFocus: searchResizeHandle.activeFocus
                                && MichiAccessibility.keyboardMode
                        }
                    }

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
                        text: (typeof library !== "undefined" && library ? library.searchTotalCount : 0) + " results"
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

                    MichiSplitButton {
                        objectName: "libraryScanSplitButton"
                        text: root.width < 760 ? "Scan" : "Scan library"
                        iconName: "library"
                        secondaryIconName: "folder"
                        iconOnly: root.width < 980
                        accessibleName: qsTr("Scan library")
                        secondaryAccessibleName: qsTr("Choose music folder")
                        enabled: !root.scanning
                            && typeof library !== "undefined" && library
                        onPrimaryClicked: root.performScan()
                        onSecondaryClicked: folderDialog.open()
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
