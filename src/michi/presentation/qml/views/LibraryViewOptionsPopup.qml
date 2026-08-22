import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Popup {
    id: root

    property string currentTab: "songs"
    property string albumMode: "grid"
    property string albumSortMode: "title"
    property bool albumSortDescending: false
    property string albumFilterMode: "all"
    property string albumTimelineGrouping: "decade"
    property real albumZoom: 1.0

    signal albumSortRequested(string mode)
    signal albumSortDirectionRequested(bool descending)
    signal albumFilterRequested(string mode)
    signal albumTimelineGroupingRequested(string mode)
    signal albumZoomRequested(real value)

    padding: MichiSpacing.md
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

    background: MichiGlassSurface {
        elevation: "modal"
        radius: MichiRadius.lg
        shadowed: true
        textured: true
        contentPadding: 0
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md
        implicitWidth: 280

        // Section: Density
        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs

            MichiText {
                text: qsTr("DENSITY")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }

            MichiSegmentedControl {
                objectName: "libraryDensityControl"
                Layout.fillWidth: true
                model: [
                    { value: "comfortable", label: qsTr("Comfortable"), icon: "density-comfortable" },
                    { value: "standard", label: qsTr("Standard"), icon: "density-standard" },
                    { value: "compact", label: qsTr("Compact"), icon: "density-compact" }
                ]
                currentValue: MichiThemeState.density
                compact: true
                accessiblePrefix: "Library density"
                Accessible.name: qsTr("Library density")
                onSelected: value => MichiThemeState.density = value
            }
        }

        // Section: Precision Mode
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiSwitch {
                id: precisionSwitch
                Layout.fillWidth: true
                text: qsTr("Precision metadata")
                checked: MichiThemeState.precisionMode
                onToggled: MichiThemeState.precisionMode = checked
            }
        }

        // Section: Artwork Size (only for Grid / PathView / Vinyl)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            visible: root.currentTab === "albums" && ["grid", "cover", "vinyl"].indexOf(root.albumMode) !== -1

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: MichiSemanticColors.borderSubtle
                opacity: 0.5
            }

            MichiText {
                text: qsTr("ARTWORK SIZE")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xs

                MichiIconButton {
                    iconName: "zoom-out"
                    accessibleName: qsTr("Make artwork smaller")
                    enabled: root.albumZoom > 0.83
                    onClicked: root.albumZoomRequested(root.albumZoom > 1.01 ? 1.0 : 0.82)
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
                    onClicked: root.albumZoomRequested(root.albumZoom < 0.99 ? 1.0 : 1.22)
                }
            }
        }

        // Section: Sort & Filter (Contextual for Albums)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            visible: root.currentTab === "albums" && root.albumMode !== "timeline"

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: MichiSemanticColors.borderSubtle
                opacity: 0.5
            }

            MichiText {
                text: qsTr("SORT & FILTER")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xs

                MichiComboBox {
                    id: sortCombo
                    Layout.fillWidth: true
                    model: ["Title", "Album artist", "Release year", "Track count", "Duration"]
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
                    iconName: root.albumSortDescending ? "sort-descending" : "sort-ascending"
                    accessibleName: root.albumSortDescending ? "Sort descending" : "Sort ascending"
                    selected: root.albumSortDescending
                    onClicked: root.albumSortDirectionRequested(!root.albumSortDescending)
                }
            }

            MichiComboBox {
                id: filterCombo
                Layout.fillWidth: true
                model: ["All albums", "With artwork", "Missing artwork", "With release year", "Unknown release year", "Hi-Res"]
                currentIndex: {
                    var map = { all: 0, artwork: 1, missingArtwork: 2, dated: 3, undated: 4, hires: 5 }
                    return map[root.albumFilterMode] || 0
                }
                onActivated: {
                    var keys = ["all", "artwork", "missingArtwork", "dated", "undated", "hires"]
                    root.albumFilterRequested(keys[currentIndex])
                }
            }
        }

        // Section: Timeline Grouping (only for Timeline view)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            visible: root.currentTab === "albums" && root.albumMode === "timeline"

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: MichiSemanticColors.borderSubtle
                opacity: 0.5
            }

            MichiText {
                text: qsTr("TIMELINE GROUPING")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }

            MichiSegmentedControl {
                Layout.fillWidth: true
                compact: true
                model: [
                    { value: "decade", label: qsTr("Decades"), icon: "view-timeline" },
                    { value: "year", label: qsTr("Years"), icon: "history" }
                ]
                currentValue: root.albumTimelineGrouping
                accessiblePrefix: "Timeline grouping"
                Accessible.name: qsTr("Timeline grouping")
                onSelected: value => root.albumTimelineGroupingRequested(value)
            }
        }
    }
}
