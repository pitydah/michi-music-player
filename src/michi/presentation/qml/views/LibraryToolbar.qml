import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    objectName: "libraryToolbar"

    property string currentTab: "songs"
    signal currentTabRequested(string tab)

    readonly property bool libraryAvailable: typeof library !== "undefined" && library
    // FREEZE FIX (FINAL EXTERNAL FREEZE AUDIT P1): el estado visual de
    // Sources deriva de la PROYECCIÓN MODERNA del Bridge (fuentes
    // configuradas), nunca de currentDir (estado legacy del pipeline
    // antiguo).
    readonly property bool hasSource: libraryAvailable
        && library.hasConfiguredSources
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
        // FREEZE FIX (audit P1): el Scan SIEMPRE pasa por el Source
        // lifecycle moderno — nunca por library.scan() (pipeline legacy).
        if (root.hasSource)
            library.scan_all_sources()
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
            Layout.minimumWidth: MichiBreakpoints.atLeastMedium(root.width)
                ? 280 : 210
            currentTab: root.currentTab
            onTabRequested: tab => root.currentTabRequested(tab)
        }

        Item { Layout.preferredWidth: MichiSpacing.xs }

        Item {
            id: searchPane
            objectName: "stableLibrarySearchPane"
            Layout.preferredWidth: MichiBreakpoints.isXl(root.width) ? 620
                : MichiBreakpoints.isWide(root.width) ? 500
                : MichiBreakpoints.isMedium(root.width) ? 420
                : MichiBreakpoints.isCompactBand(root.width) ? 360 : 320
            Layout.minimumWidth: MichiBreakpoints.atLeastMedium(root.width)
                ? 320 : 280
            Layout.maximumWidth: 700
            Layout.fillHeight: true

            RowLayout {
                anchors.fill: parent
                spacing: MichiSpacing.sm

                MichiSearchField {
                    id: searchInput
                    Layout.fillWidth: true
                    Layout.minimumWidth: MichiBreakpoints.atLeastMedium(root.width)
                        ? 210 : 130
                    text: root.libraryAvailable ? library.searchQuery : ""
                    placeholderText: root.searchPlaceholder()
                    onEdited: query => { if (root.libraryAvailable) library.search(query) }
                    onClearRequested: { if (root.libraryAvailable) library.clear_search() }
                }

                // Fixed slot: result/scanning text never moves the search field.
                Item {
                    Layout.preferredWidth: MichiBreakpoints.atLeastMedium(root.width)
                        ? 82 : 48
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
                        objectName: "librarySourcePopover"
                        x: -326
                        y: parent.height + MichiSpacing.xs
                    }
                }

                MichiButton {
                    visible: !root.scanning
                    text: root.hasSource
                        ? (MichiBreakpoints.isCompact(root.width)
                            ? qsTr("Scan") : qsTr("Scan library"))
                        : qsTr("Choose folder")
                    iconName: root.hasSource ? "library" : "folder"
                    variant: "secondary"
                    iconOnly: !MichiBreakpoints.atLeastWide(root.width)
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

                // M6.9 REOPENED — Enrich Library: acción global EXPLÍCITA
                // (nunca automática tras scan; Online Library Enrichment
                // debe estar ON). Progreso real del backend, no fabricado.
                MichiButton {
                    id: enrichButton
                    visible: !root.scanning
                        && typeof enrichment !== "undefined" && enrichment
                        && enrichment.onlineEnabled
                    text: {
                        if (enrichment.enrichmentJobState === "RUNNING"
                                || enrichment.enrichmentJobState === "PREPARING"
                                || enrichment.enrichmentJobState === "CANCELLING")
                            return qsTr("Enriching Library… %1 / %2")
                                .arg(enrichment.enrichmentJobProcessed)
                                .arg(enrichment.enrichmentJobTotal)
                        return qsTr("Enrich Library")
                    }
                    iconName: enrichment.enrichmentJobState === "IDLE"
                        ? "sparkles" : ""
                    variant: "ghost"
                    iconOnly: MichiBreakpoints.isCompact(root.width)
                        && enrichment.enrichmentJobState === "IDLE"
                    enabled: root.libraryAvailable
                    accessibleName: qsTr("Enrich entire library")
                    onClicked: {
                        if (enrichment.enrichmentJobState === "RUNNING"
                                || enrichment.enrichmentJobState === "PREPARING"
                                || enrichment.enrichmentJobState === "CANCELLING")
                            enrichment.cancel_library_enrichment()
                        else
                            enrichment.start_library_enrichment()
                    }
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
