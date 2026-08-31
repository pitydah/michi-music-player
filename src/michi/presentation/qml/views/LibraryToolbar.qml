import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root

    property string currentTab: "songs"
    signal currentTabRequested(string tab)

    readonly property bool libraryAvailable: typeof library !== "undefined" && library
    readonly property bool hasSource: libraryAvailable && library.currentDir.length > 0
    readonly property bool scanning: libraryAvailable
        && library.scanStatus !== ""
        && library.scanStatus !== "IDLE"
        && library.scanStatus !== "COMPLETED"
        && library.scanStatus !== "CANCELLED"
        && library.scanStatus !== "FAILED"

    elevation: "subtle"
    tileSeed: 2
    shadowed: true
    textured: true
    accented: root.scanning || (root.libraryAvailable && library.scanStatus === "FAILED")
    accentColor: root.libraryAvailable && library.scanStatus === "FAILED"
        ? MichiPalette.error : MichiPalette.auroraCyan
    contentPadding: MichiSpacing.md
    implicitHeight: MichiMetrics.controlLarge + MichiSpacing.md * 2

    function searchPlaceholder() {
        if (currentTab === "albums") return qsTr("Search albums or album artists…")
        if (currentTab === "artists") return qsTr("Search artists…")
        if (currentTab === "genres") return qsTr("Search genres…")
        if (currentTab === "playlists") return qsTr("Search tracks or playlists…")
        return qsTr("Search title, artist, album, genre or composer…")
    }

    function performScan() {
        if (!root.libraryAvailable || root.scanning)
            return
        if (root.hasSource)
            library.scan(library.currentDir)
        else
            sourcePopover.open()
    }

    RowLayout {
        id: toolbarContent
        anchors.fill: parent
        spacing: MichiSpacing.sm

        LibraryTabs {
            id: libraryNavigation
            Layout.fillWidth: true
            Layout.minimumWidth: 280
            currentTab: root.currentTab
            onTabRequested: tab => root.currentTabRequested(tab)
        }

        Item { Layout.preferredWidth: MichiSpacing.xs }

        Item {
            id: searchPane
            objectName: "stableLibrarySearchPane"
            Layout.preferredWidth: root.width >= 1480 ? 620
                : root.width >= 1120 ? 500 : 390
            Layout.minimumWidth: 300
            Layout.maximumWidth: 700
            Layout.fillHeight: true

            RowLayout {
                anchors.fill: parent
                spacing: MichiSpacing.sm

                MichiSearchField {
                    id: searchInput
                    Layout.fillWidth: true
                    Layout.minimumWidth: 210
                    text: root.libraryAvailable ? library.searchQuery : ""
                    placeholderText: root.searchPlaceholder()
                    onEdited: query => { if (root.libraryAvailable) library.search(query) }
                    onClearRequested: { if (root.libraryAvailable) library.clear_search() }
                }

                // Fixed slot: result/scanning text never moves the search field.
                Item {
                    Layout.preferredWidth: 82
                    Layout.fillHeight: true

                    MichiText {
                        objectName: "scanStatusText"
                        anchors.centerIn: parent
                        width: parent.width
                        visible: root.scanning
                        text: root.libraryAvailable
                            ? library.scanStatus + " · " + library.scanProcessed
                                + " / " + library.scanTotal : ""
                        role: "technical"
                        technical: true
                        horizontalAlignment: Text.AlignRight
                        color: MichiPalette.auroraCyan
                        elide: Text.ElideRight
                    }

                    MichiText {
                        objectName: "searchNoResultsText"
                        anchors.centerIn: parent
                        width: parent.width
                        visible: !root.scanning && root.libraryAvailable
                            && library.searchActive && library.searchTotalCount === 0
                        text: qsTr("No results")
                        role: "technical"
                        technical: true
                        horizontalAlignment: Text.AlignRight
                        color: MichiPalette.warning
                        elide: Text.ElideRight
                    }

                    MichiText {
                        anchors.centerIn: parent
                        width: parent.width
                        visible: !root.scanning && root.libraryAvailable
                            && library.searchActive && library.searchTotalCount > 0
                        text: root.libraryAvailable
                            ? qsTr("%1 results").arg(library.searchTotalCount) : ""
                        role: "technical"
                        technical: true
                        horizontalAlignment: Text.AlignRight
                        color: MichiPalette.textMuted
                        elide: Text.ElideRight
                    }
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
                        onClicked: sourcePopover.visible
                            ? sourcePopover.close() : sourcePopover.open()
                    }

                    LibrarySourcePopover {
                        id: sourcePopover
                        x: -326
                        y: parent.height + MichiSpacing.xs
                    }
                }

                MichiButton {
                    visible: !root.scanning
                    text: root.hasSource
                        ? (root.width < 900 ? qsTr("Scan") : qsTr("Scan library"))
                        : qsTr("Choose folder")
                    iconName: root.hasSource ? "library" : "folder"
                    variant: "secondary"
                    iconOnly: root.width < 980
                    accessibleName: root.hasSource
                        ? qsTr("Scan library") : qsTr("Choose music folder")
                    enabled: root.libraryAvailable
                    onClicked: root.performScan()
                }

                MichiButton {
                    visible: root.scanning
                    text: qsTr("Cancel")
                    iconName: "close"
                    variant: "secondary"
                    onClicked: { if (root.libraryAvailable) library.cancel_scan() }
                }
            }
        }
    }

    // Progress is painted inside the fixed toolbar bounds; content never jumps.
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 2
        color: "transparent"
        visible: root.scanning

        Rectangle {
            height: parent.height
            width: root.libraryAvailable ? parent.width * library.scanProgress : 0
            color: MichiPalette.auroraCyan
            Behavior on width {
                enabled: !MichiAccessibility.reducedMotion
                NumberAnimation {
                    duration: MichiMotion.standard
                    easing.type: MichiMotion.outCubic
                }
            }
        }
    }
}
