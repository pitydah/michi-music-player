import QtQuick
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

PageHeader {
    id: root

    property string currentTab: "songs"
    property string albumMode: "grid"
    signal albumModeRequested(string mode)
    readonly property bool albumViewsVisible: currentTab === "albums"
        && library.selectedAlbumKey === ""
    readonly property var albumViewModes: [
        { value: "grid", label: "Grid", icon: "view-grid" },
        { value: "cover", label: "PathView", icon: "view-path" },
        { value: "vinyl", label: "Vinyl Wall", icon: "view-vinyl" },
        { value: "timeline", label: "Timeline", icon: "view-timeline" },
        { value: "magazine", label: "Magazine", icon: "view-magazine" },
        { value: "list", label: "List", icon: "view-list" }
    ]
    readonly property bool precisionRelevant: [
        "songs", "albums", "favorites", "history", "recently", "playlists"
    ].indexOf(currentTab) !== -1

    title: "Library"
    subtitle: library.fileCount > 0
        ? library.fileCount + " tracks · " + library.albumCount + " albums · "
            + library.artistCount + " artists"
        : "Your local music collection"

    MichiText {
        visible: root.albumViewsVisible && root.width >= 1120
        text: "VIEWS"
        role: "technical"
        technical: true
        color: MichiPalette.textMuted
    }

    MichiSegmentedControl {
        objectName: "albumViewSwitcher"
        visible: root.albumViewsVisible
        model: root.albumViewModes
        currentValue: root.albumMode
        compact: true
        accessiblePrefix: "Album view"
        Accessible.name: "Album view"
        onSelected: value => root.albumModeRequested(value)
    }

    Rectangle {
        visible: root.albumViewsVisible && root.width >= 840
        Layout.preferredWidth: 1
        Layout.preferredHeight: 26
        color: MichiSemanticColors.borderSubtle
    }

    MichiText {
        visible: root.width >= 920
        text: "DENSITY"
        role: "technical"
        technical: true
        color: MichiPalette.textMuted
    }

    MichiSegmentedControl {
        objectName: "libraryDensityControl"
        model: [
            { value: "comfortable", label: "Comfortable", icon: "density-comfortable" },
            { value: "standard", label: "Standard", icon: "density-standard" },
            { value: "compact", label: "Compact", icon: "density-compact" }
        ]
        currentValue: MichiThemeState.density
        compact: true
        accessiblePrefix: "Library density"
        Accessible.name: "Library density"
        onSelected: value => MichiThemeState.density = value
    }

    Rectangle {
        visible: root.precisionRelevant && root.width >= 760
        Layout.preferredWidth: 1
        Layout.preferredHeight: 26
        color: MichiSemanticColors.borderSubtle
    }

    MichiSwitch {
        visible: root.precisionRelevant && root.width >= 760
        text: root.width < 1800 ? "Precision" : "Precision metadata"
        checked: MichiThemeState.precisionMode
        onToggled: MichiThemeState.precisionMode = checked
    }
}
