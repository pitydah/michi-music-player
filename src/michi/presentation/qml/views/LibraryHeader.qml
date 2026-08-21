import QtQuick
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

PageHeader {
    id: root

    property string currentTab: "songs"
    readonly property bool precisionRelevant: [
        "songs", "albums", "favorites", "history", "recently", "playlists"
    ].indexOf(currentTab) !== -1

    title: "Library"
    subtitle: library.fileCount > 0
        ? library.fileCount + " tracks · " + library.albumCount + " albums · "
            + library.artistCount + " artists"
        : "Your local music collection"

    MichiText {
        visible: root.width >= 1120
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
        compact: root.width < 1120
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
        text: root.width < 1180 ? "Precision" : "Precision metadata"
        checked: MichiThemeState.precisionMode
        onToggled: MichiThemeState.precisionMode = checked
    }
}
