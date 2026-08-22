import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root

    property string currentTab: "songs"
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

    // Shared scan entry point (toolbar button + empty-library CTA): scans the
    // configured directory or opens the source picker when none is set.
    function performScan() {
        if (typeof library === "undefined" || !library)
            return
        if (library.currentDir.length > 0)
            library.scan(library.currentDir)
        else
            sourcePopover.open()
    }

    ColumnLayout {
        id: toolbarContent
        anchors.fill: parent
        spacing: MichiSpacing.sm

        SplitView {
            id: navigationSplit
            objectName: "libraryNavigationSplitView"
            Layout.fillWidth: true
            Layout.preferredHeight: MichiMetrics.controlLarge
            orientation: Qt.Horizontal

            handle: Item {
                implicitWidth: 16
                implicitHeight: navigationSplit.height
                HoverHandler {
                    id: navigationHandleHover
                    cursorShape: Qt.SplitHCursor
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: 1
                    height: 20
                    color: navigationHandleHover.hovered
                        ? MichiSemanticColors.auroraCyanBorder
                        : MichiSemanticColors.borderSubtle
                }
            }

            LibraryTabs {
                id: libraryNavigation
                SplitView.fillWidth: true
                SplitView.minimumWidth: 300
                currentTab: root.currentTab
                onTabRequested: tab => root.currentTabRequested(tab)
            }

            Item {
                id: searchPane
                objectName: "resizableLibrarySearchPane"
                SplitView.preferredWidth: root.width >= 1480 ? 640 : 520
                SplitView.minimumWidth: root.width < 980 ? 360 : 430
                SplitView.maximumWidth: 760

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

                    Item {
                        Layout.preferredWidth: MichiMetrics.controlMedium
                        Layout.preferredHeight: MichiMetrics.controlMedium

                        MichiIconButton {
                            id: sourceBtn
                            anchors.fill: parent
                            iconName: "folder"
                            selected: sourcePopover.visible
                            accessibleName: qsTr("Music folder source")
                            onClicked: {
                                if (sourcePopover.visible)
                                    sourcePopover.close()
                                else
                                    sourcePopover.open()
                            }
                        }

                        LibrarySourcePopover {
                            id: sourcePopover
                            x: -326
                            y: parent.height + MichiSpacing.xs
                        }
                    }

                    MichiButton {
                        text: root.width < 760 ? "Scan" : "Scan library"
                        iconName: "library"
                        variant: "secondary"
                        iconOnly: root.width < 980
                        accessibleName: qsTr("Scan library")
                        enabled: !root.scanning
                            && typeof library !== "undefined" && library
                            && library.currentDir.length > 0
                        onClicked: root.performScan()
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
