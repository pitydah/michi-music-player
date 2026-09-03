pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Popup {
    id: root
    objectName: "libraryViewOptionsPopup"

    property string currentTab: "songs"
    property string albumMode: "grid"
    property string displayedMode: albumMode
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0
    property var viewPreferences: ({})

    signal albumSortRequested(string mode)
    signal albumSortDirectionRequested(bool descending)
    signal albumFilterRequested(string mode)
    signal albumTimelineGroupingRequested(string mode)
    signal albumZoomRequested(real value)
    signal viewPreferenceRequested(string section, string key, var value)
    signal resetViewRequested(string section)

    padding: MichiSpacing.md
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

    onAlbumModeChanged: {
        if (!opened || MichiAccessibility.reducedMotion) {
            displayedMode = albumMode
            contextualLoader.opacity = 1
        } else {
            contextualSwap.restart()
        }
    }
    onOpenedChanged: if (opened) {
        displayedMode = albumMode
        contextualLoader.opacity = 1
    }

    enter: Transition {
        ParallelAnimation {
            NumberAnimation {
                property: "opacity"; from: 0; to: 1
                duration: MichiAccessibility.reducedMotion ? 0 : MichiMotion.popupOpen
                easing.type: MichiMotion.outCubic
            }
            NumberAnimation {
                property: "scale"; from: 0.985; to: 1
                duration: MichiAccessibility.reducedMotion ? 0 : MichiMotion.popupOpen
                easing.type: MichiMotion.outCubic
            }
        }
    }
    exit: Transition {
        ParallelAnimation {
            NumberAnimation {
                property: "opacity"; from: 1; to: 0
                duration: MichiAccessibility.reducedMotion ? 0 : MichiMotion.popupClose
            }
            NumberAnimation {
                property: "scale"; from: 1; to: 0.985
                duration: MichiAccessibility.reducedMotion ? 0 : MichiMotion.popupClose
            }
        }
    }

    background: MichiGlassSurface {
        elevation: "modal"
        materialRole: MichiMaterialRole.modal
        tileSeed: 4
        radius: MichiRadius.lg
        shadowed: true
        textured: true
        glintMode: "edge"
        contentPadding: 0
    }

    function sectionName(mode) {
        switch (mode === undefined ? root.albumMode : mode) {
            case "cover": return "flow"
            case "vinyl": return "vinyl"
            case "timeline": return "chronology"
            case "magazine": return "editorial"
            case "list": return "studioList"
            default: return "gallery"
        }
    }

    function modeLabel(mode) {
        switch (mode === undefined ? root.albumMode : mode) {
            case "cover": return qsTr("Album Flow")
            case "vinyl": return qsTr("Listening Wall")
            case "timeline": return qsTr("Chronology")
            case "magazine": return qsTr("Editorial")
            case "list": return qsTr("Studio List")
            default: return qsTr("Gallery")
        }
    }

    function pref(section, key, fallback) {
        return root.viewPreferences && root.viewPreferences[section]
            && root.viewPreferences[section][key] !== undefined
            ? root.viewPreferences[section][key] : fallback
    }

    function indexOf(model, value) {
        for (var i = 0; i < model.length; ++i) {
            if (model[i].value === value)
                return i
        }
        return 0
    }

    function defaultValues(section) {
        var defaults = {
            gallery: { artworkSize: "medium", spacing: "balanced",
                metadataLevel: "standard", quickActions: true,
                precisionMetadata: false, inspector: true },
            flow: { coverSize: "standard", visibleAlbums: "auto",
                depth: "standard", ambientColor: true,
                metadataLevel: "standard" },
            vinyl: { sleeveSize: "standard", spacing: "standard",
                reveal: "standard", metadataLevel: "standard",
                artworkLabel: true, inspector: true },
            chronology: { grouping: "decade", direction: "newest",
                density: "standard", metadataLevel: "standard",
                showPeriodDensity: false },
            editorial: { heroVisible: true, informationRichness: "standard",
                cachedEnrichmentVisible: true, archiveLayout: "list" },
            studioList: { density: "standard", artworkSize: "small",
                precisionMetadata: true, inspector: true, artistColumn: true,
                yearColumn: true, tracksColumn: true, durationColumn: true,
                formatColumn: true }
        }
        return defaults[section] || ({})
    }

    function optionLabel(key) {
        var labels = {
            artworkSize: qsTr("Artwork size"), spacing: qsTr("Spacing"),
            metadataLevel: qsTr("Metadata"), quickActions: qsTr("Quick actions"),
            precisionMetadata: qsTr("Precision metadata"), inspector: qsTr("Inspector"),
            coverSize: qsTr("Cover size"), visibleAlbums: qsTr("Visible albums"),
            depth: qsTr("Depth"), ambientColor: qsTr("Ambient color"),
            sleeveSize: qsTr("Sleeve size"), reveal: qsTr("Vinyl reveal"),
            artworkLabel: qsTr("Artwork label"), grouping: qsTr("Grouping"),
            direction: qsTr("Direction"), density: qsTr("Density"),
            showPeriodDensity: qsTr("Collection density"), heroVisible: qsTr("Hero"),
            informationRichness: qsTr("Information richness"),
            cachedEnrichmentVisible: qsTr("Saved online context"),
            archiveLayout: qsTr("Archive layout"), artistColumn: qsTr("Artist column"),
            yearColumn: qsTr("Year column"), tracksColumn: qsTr("Tracks column"),
            durationColumn: qsTr("Duration column"), formatColumn: qsTr("Format column")
        }
        return labels[key] || key
    }

    function displayValue(value) {
        if (typeof value === "boolean")
            return value ? qsTr("On") : qsTr("Off")
        return String(value).replace(/([A-Z])/g, " $1")
    }

    function activeCustomizations() {
        var items = []
        if (root.albumFilterMode !== "all")
            items.push({ kind: "filter", label: qsTr("Album filter · %1")
                .arg(root.displayValue(root.albumFilterMode)) })
        if (root.displayedMode !== "timeline"
                && (root.albumSortMode !== "title" || root.albumSortDescending))
            items.push({ kind: "sort", label: qsTr("Sort · %1%2")
                .arg(root.displayValue(root.albumSortMode))
                .arg(root.albumSortDescending ? qsTr(" · descending") : "") })
        var section = root.sectionName(root.displayedMode)
        var defaults = root.defaultValues(section)
        var current = root.viewPreferences && root.viewPreferences[section]
            ? root.viewPreferences[section] : ({})
        var keys = Object.keys(defaults)
        for (var i = 0; i < keys.length; ++i) {
            var key = keys[i]
            var value = current[key] === undefined ? defaults[key] : current[key]
            if (value !== defaults[key])
                items.push({ kind: "view", section: section, key: key,
                    defaultValue: defaults[key], label: root.optionLabel(key)
                        + " · " + root.displayValue(value) })
        }
        return items
    }

    function clearCustomization(item) {
        if (item.kind === "filter")
            root.albumFilterRequested("all")
        else if (item.kind === "sort") {
            root.albumSortRequested("title")
            root.albumSortDirectionRequested(false)
        } else if (item.kind === "view")
            root.viewPreferenceRequested(item.section, item.key, item.defaultValue)
    }

    contentItem: ColumnLayout {
        id: popupContent
        spacing: MichiSpacing.md
        implicitWidth: 320

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiIcon {
                name: "view-options"
                Layout.preferredWidth: MichiMetrics.iconMedium
                Layout.preferredHeight: MichiMetrics.iconMedium
                iconColor: MichiPalette.auroraCyan
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                MichiText {
                    text: root.modeLabel(root.displayedMode).toUpperCase()
                    role: "technical"
                    technical: true
                    font.weight: Font.DemiBold
                }
                MichiText {
                    text: qsTr("Customize this view")
                    role: "caption"
                    color: MichiPalette.textMuted
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: MichiSemanticColors.borderSubtle
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            visible: root.currentTab === "albums"

            MichiText {
                text: qsTr("SORT & FILTER")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xs
                visible: root.displayedMode !== "timeline"
                MichiComboBox {
                    Layout.fillWidth: true
                    model: [qsTr("Title"), qsTr("Album artist"), qsTr("Release year"), qsTr("Track count"), qsTr("Duration")]
                    currentIndex: {
                        var map = { title: 0, artist: 1, year: 2, tracks: 3, duration: 4 }
                        return map[root.albumSortMode] || 0
                    }
                    onActivated: {
                        var keys = ["title", "artist", "year", "tracks", "duration"]
                        root.albumSortRequested(keys[currentIndex])
                    }
                }
                MichiIconButton {
                    iconName: root.albumSortDescending
                        ? "sort-descending" : "sort-ascending"
                    accessibleName: root.albumSortDescending
                        ? qsTr("Sort descending") : qsTr("Sort ascending")
                    selected: root.albumSortDescending
                    onClicked: root.albumSortDirectionRequested(!root.albumSortDescending)
                }
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("All albums"), qsTr("With artwork"), qsTr("Missing artwork"), qsTr("With release year"), qsTr("Unknown release year"), qsTr("24-bit / ≥96 kHz / DSD")]
                currentIndex: {
                    var map = { all: 0, artwork: 1, missingArtwork: 2,
                        dated: 3, undated: 4, hires: 5 }
                    return map[root.albumFilterMode] || 0
                }
                onActivated: {
                    var keys = ["all", "artwork", "missingArtwork", "dated", "undated", "hires"]
                    root.albumFilterRequested(keys[currentIndex])
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            visible: activeRepeater.count > 0
            MichiText {
                text: qsTr("ACTIVE")
                role: "technical"
                technical: true
                color: MichiPalette.auroraCyan
            }
            Repeater {
                id: activeRepeater
                model: root.activeCustomizations()
                delegate: RowLayout {
                    id: activeRow
                    required property var modelData
                    Layout.fillWidth: true
                    MichiText {
                        Layout.fillWidth: true
                        text: activeRow.modelData.label
                        role: "caption"
                        color: MichiPalette.textSecondary
                        elide: Text.ElideRight
                    }
                    MichiIconButton {
                        Layout.preferredWidth: MichiMetrics.controlSmall
                        Layout.preferredHeight: MichiMetrics.controlSmall
                        iconName: "close"
                        accessibleName: qsTr("Clear %1")
                            .arg(activeRow.modelData.label)
                        onClicked: root.clearCustomization(activeRow.modelData)
                    }
                }
            }
        }

        Loader {
            id: contextualLoader
            Layout.fillWidth: true
            sourceComponent: root.displayedMode === "cover" ? flowOptions
                : root.displayedMode === "vinyl" ? vinylOptions
                : root.displayedMode === "timeline" ? chronologyOptions
                : root.displayedMode === "magazine" ? editorialOptions
                : root.displayedMode === "list" ? studioOptions : galleryOptions
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: MichiSemanticColors.borderSubtle
        }

        MichiButton {
            Layout.fillWidth: true
            text: qsTr("Reset %1").arg(root.modeLabel(root.displayedMode))
            iconName: "reset"
            variant: "ghost"
            onClicked: root.resetViewRequested(root.sectionName(root.displayedMode))
        }
    }

    SequentialAnimation {
        id: contextualSwap
        NumberAnimation {
            target: contextualLoader
            property: "opacity"
            to: 0
            duration: MichiAccessibility.reducedMotion ? 0 : MichiMotion.micro
        }
        ScriptAction { script: root.displayedMode = root.albumMode }
        NumberAnimation {
            target: contextualLoader
            property: "opacity"
            to: 1
            duration: MichiAccessibility.reducedMotion ? 0 : MichiMotion.standard
        }
    }

    component OptionLabel: MichiText {
        role: "technical"
        technical: true
        color: MichiPalette.textMuted
    }

    Component {
        id: galleryOptions
        ColumnLayout {
            spacing: MichiSpacing.sm
            OptionLabel { text: qsTr("GALLERY") }
            // POST-MERGE SEMANTIC RECOVERY (P1-01): control directo de
            // ARTWORK SIZE — el zoom modifica la geometría REAL de las
            // cards (82% / 100% / 122% vía albumZoomRequested →
            // LibraryView.requestAlbumZoom).
            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xs

                MichiIconButton {
                    iconName: "zoom-out"
                    accessibleName: qsTr("Make artwork smaller")
                    enabled: root.albumZoom > 0.83
                    onClicked: root.albumZoomRequested(
                        root.albumZoom > 1.01 ? 1.0 : 0.82)
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    radius: MichiRadius.md
                    color: root.albumZoom === 1.0
                        ? MichiSemanticColors.controlSurface
                        : MichiSemanticColors.auroraCyanSurface
                    border.width: 1
                    border.color: root.albumZoom === 1.0
                        ? MichiSemanticColors.borderSubtle
                        : MichiSemanticColors.auroraCyanBorderSubtle

                    MichiText {
                        anchors.centerIn: parent
                        text: Math.round(root.albumZoom * 100) + "%"
                        role: "technical"
                        technical: true
                        color: root.albumZoom === 1.0
                            ? MichiPalette.textSecondary
                            : MichiPalette.auroraCyan
                        font.weight: Font.DemiBold
                    }
                }

                MichiIconButton {
                    iconName: "zoom-in"
                    accessibleName: qsTr("Make artwork larger")
                    enabled: root.albumZoom < 1.21
                    onClicked: root.albumZoomRequested(
                        root.albumZoom < 0.99 ? 1.0 : 1.22)
                }
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Small artwork"), qsTr("Medium artwork"), qsTr("Large artwork")]
                currentIndex: ({ small: 0, medium: 1, large: 2 })[root.pref("gallery", "artworkSize", "medium")]
                onActivated: root.viewPreferenceRequested("gallery", "artworkSize", ["small", "medium", "large"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Tight spacing"), qsTr("Balanced spacing"), qsTr("Airy spacing")]
                currentIndex: ({ tight: 0, balanced: 1, airy: 2 })[root.pref("gallery", "spacing", "balanced")]
                onActivated: root.viewPreferenceRequested("gallery", "spacing", ["tight", "balanced", "airy"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Minimal metadata"), qsTr("Standard metadata"), qsTr("Detailed metadata")]
                currentIndex: ({ minimal: 0, standard: 1, detailed: 2 })[root.pref("gallery", "metadataLevel", "standard")]
                onActivated: root.viewPreferenceRequested("gallery", "metadataLevel", ["minimal", "standard", "detailed"][currentIndex])
            }
            MichiSwitch {
                Layout.fillWidth: true
                text: qsTr("Quick Play on hover")
                checked: root.pref("gallery", "quickActions", true)
                onToggled: root.viewPreferenceRequested("gallery", "quickActions", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true
                text: qsTr("Precision metadata")
                checked: root.pref("gallery", "precisionMetadata", false)
                onToggled: root.viewPreferenceRequested("gallery", "precisionMetadata", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true
                text: qsTr("Selection inspector")
                checked: root.pref("gallery", "inspector", true)
                onToggled: root.viewPreferenceRequested("gallery", "inspector", checked)
            }
        }
    }

    Component {
        id: flowOptions
        ColumnLayout {
            spacing: MichiSpacing.sm
            OptionLabel { text: qsTr("ALBUM FLOW") }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Small covers"), qsTr("Standard covers"), qsTr("Large covers")]
                currentIndex: ({ small: 0, standard: 1, large: 2 })[root.pref("flow", "coverSize", "standard")]
                onActivated: root.viewPreferenceRequested("flow", "coverSize", ["small", "standard", "large"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Albums: Auto"), qsTr("Albums: 5"), qsTr("Albums: 7"), qsTr("Albums: 9")]
                currentIndex: ({ auto: 0, "5": 1, "7": 2, "9": 3 })[root.pref("flow", "visibleAlbums", "auto")]
                onActivated: root.viewPreferenceRequested("flow", "visibleAlbums", ["auto", "5", "7", "9"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Subtle depth"), qsTr("Standard depth"), qsTr("Immersive depth")]
                currentIndex: ({ subtle: 0, standard: 1, immersive: 2 })[root.pref("flow", "depth", "standard")]
                onActivated: root.viewPreferenceRequested("flow", "depth", ["subtle", "standard", "immersive"][currentIndex])
            }
            MichiSwitch {
                Layout.fillWidth: true
                text: qsTr("Ambient artwork color")
                checked: root.pref("flow", "ambientColor", true)
                onToggled: root.viewPreferenceRequested("flow", "ambientColor", checked)
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Minimal selection info"), qsTr("Standard selection info"), qsTr("Detailed selection info")]
                currentIndex: ({ minimal: 0, standard: 1, detailed: 2 })[root.pref("flow", "metadataLevel", "standard")]
                onActivated: root.viewPreferenceRequested("flow", "metadataLevel", ["minimal", "standard", "detailed"][currentIndex])
            }
        }
    }

    Component {
        id: vinylOptions
        ColumnLayout {
            spacing: MichiSpacing.sm
            OptionLabel { text: qsTr("LISTENING WALL") }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Small sleeves"), qsTr("Standard sleeves"), qsTr("Large sleeves")]
                currentIndex: ({ small: 0, standard: 1, large: 2 })[root.pref("vinyl", "sleeveSize", "standard")]
                onActivated: root.viewPreferenceRequested("vinyl", "sleeveSize", ["small", "standard", "large"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Tight wall"), qsTr("Standard wall"), qsTr("Gallery wall")]
                currentIndex: ({ tight: 0, standard: 1, gallery: 2 })[root.pref("vinyl", "spacing", "standard")]
                onActivated: root.viewPreferenceRequested("vinyl", "spacing", ["tight", "standard", "gallery"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Subtle reveal"), qsTr("Standard reveal"), qsTr("Pronounced reveal")]
                currentIndex: ({ subtle: 0, standard: 1, pronounced: 2 })[root.pref("vinyl", "reveal", "standard")]
                onActivated: root.viewPreferenceRequested("vinyl", "reveal", ["subtle", "standard", "pronounced"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Minimal metadata"), qsTr("Standard metadata"), qsTr("Detailed metadata")]
                currentIndex: ({ minimal: 0, standard: 1, detailed: 2 })[root.pref("vinyl", "metadataLevel", "standard")]
                onActivated: root.viewPreferenceRequested("vinyl", "metadataLevel", ["minimal", "standard", "detailed"][currentIndex])
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Match disc label to artwork")
                checked: root.pref("vinyl", "artworkLabel", true)
                onToggled: root.viewPreferenceRequested("vinyl", "artworkLabel", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Selection inspector")
                checked: root.pref("vinyl", "inspector", true)
                onToggled: root.viewPreferenceRequested("vinyl", "inspector", checked)
            }
        }
    }

    Component {
        id: chronologyOptions
        ColumnLayout {
            spacing: MichiSpacing.sm
            OptionLabel { text: qsTr("CHRONOLOGY") }
            MichiSegmentedControl {
                Layout.fillWidth: true
                compact: true
                model: [{ value: "decade", label: qsTr("Decades") }, { value: "year", label: qsTr("Years") }]
                currentValue: root.pref("chronology", "grouping", "decade")
                onSelected: value => root.albumTimelineGroupingRequested(value)
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Newest first"), qsTr("Oldest first")]
                currentIndex: root.pref("chronology", "direction", "newest") === "oldest" ? 1 : 0
                onActivated: root.viewPreferenceRequested("chronology", "direction", currentIndex === 0 ? "newest" : "oldest")
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Compact timeline"), qsTr("Standard timeline"), qsTr("Expanded timeline")]
                currentIndex: ({ compact: 0, standard: 1, expanded: 2 })[root.pref("chronology", "density", "standard")]
                onActivated: root.viewPreferenceRequested("chronology", "density", ["compact", "standard", "expanded"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Minimal information"), qsTr("Standard information"), qsTr("Detailed information")]
                currentIndex: ({ minimal: 0, standard: 1, detailed: 2 })[root.pref("chronology", "metadataLevel", "standard")]
                onActivated: root.viewPreferenceRequested("chronology", "metadataLevel", ["minimal", "standard", "detailed"][currentIndex])
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Show collection density")
                checked: root.pref("chronology", "showPeriodDensity", false)
                onToggled: root.viewPreferenceRequested("chronology", "showPeriodDensity", checked)
            }
        }
    }

    Component {
        id: editorialOptions
        ColumnLayout {
            spacing: MichiSpacing.sm
            OptionLabel { text: qsTr("EDITORIAL") }
            MichiSwitch {
                Layout.fillWidth: true
                text: qsTr("Featured album hero")
                checked: root.pref("editorial", "heroVisible", true)
                onToggled: root.viewPreferenceRequested("editorial", "heroVisible", checked)
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Minimal information"), qsTr("Standard information"), qsTr("Rich information")]
                currentIndex: ({ minimal: 0, standard: 1, rich: 2 })[root.pref("editorial", "informationRichness", "standard")]
                onActivated: root.viewPreferenceRequested("editorial", "informationRichness", ["minimal", "standard", "rich"][currentIndex])
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Show saved online context")
                checked: root.pref("editorial", "cachedEnrichmentVisible", true)
                onToggled: root.viewPreferenceRequested("editorial", "cachedEnrichmentVisible", checked)
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Archive list"), qsTr("Compact archive grid")]
                currentIndex: root.pref("editorial", "archiveLayout", "list") === "compactGrid" ? 1 : 0
                onActivated: root.viewPreferenceRequested("editorial", "archiveLayout", currentIndex === 0 ? "list" : "compactGrid")
            }
        }
    }

    Component {
        id: studioOptions
        ColumnLayout {
            spacing: MichiSpacing.sm
            OptionLabel { text: qsTr("STUDIO LIST") }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("Compact rows"), qsTr("Standard rows"), qsTr("Comfortable rows")]
                currentIndex: ({ compact: 0, standard: 1, comfortable: 2 })[root.pref("studioList", "density", "standard")]
                onActivated: root.viewPreferenceRequested("studioList", "density", ["compact", "standard", "comfortable"][currentIndex])
            }
            MichiComboBox {
                Layout.fillWidth: true
                model: [qsTr("No artwork"), qsTr("Small artwork"), qsTr("Standard artwork")]
                currentIndex: ({ none: 0, small: 1, standard: 2 })[root.pref("studioList", "artworkSize", "small")]
                onActivated: root.viewPreferenceRequested("studioList", "artworkSize", ["none", "small", "standard"][currentIndex])
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Artist column")
                checked: root.pref("studioList", "artistColumn", true)
                onToggled: root.viewPreferenceRequested("studioList", "artistColumn", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Year column")
                checked: root.pref("studioList", "yearColumn", true)
                onToggled: root.viewPreferenceRequested("studioList", "yearColumn", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Tracks column")
                checked: root.pref("studioList", "tracksColumn", true)
                onToggled: root.viewPreferenceRequested("studioList", "tracksColumn", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Duration column")
                checked: root.pref("studioList", "durationColumn", true)
                onToggled: root.viewPreferenceRequested("studioList", "durationColumn", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Format column")
                checked: root.pref("studioList", "formatColumn", true)
                onToggled: root.viewPreferenceRequested("studioList", "formatColumn", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Precision metadata")
                checked: root.pref("studioList", "precisionMetadata", true)
                onToggled: root.viewPreferenceRequested("studioList", "precisionMetadata", checked)
            }
            MichiSwitch {
                Layout.fillWidth: true; text: qsTr("Selection inspector")
                checked: root.pref("studioList", "inspector", true)
                onToggled: root.viewPreferenceRequested("studioList", "inspector", checked)
            }
        }
    }
}
