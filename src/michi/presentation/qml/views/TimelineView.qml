import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../media"
import "../primitives"
import "../theme"

ListView {
    id: albumTimeline
    objectName: "albumTimelineView"

    property var albumModel: library.timelineAlbums
    property bool groupByDecade: true

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    spacing: MichiSpacing.xs
    cacheBuffer: height
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    section.property: groupByDecade ? "decade" : "year"
    section.criteria: ViewSection.FullString
    section.labelPositioning: ViewSection.CurrentLabelAtStart
        | ViewSection.InlineLabels
    Accessible.role: Accessible.List
    Accessible.name: "Album timeline"
    Accessible.description: "Albums grouped chronologically"

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }

    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        width: MichiSpacing.sm
    }

    section.delegate: Item {
        required property string section
        width: albumTimeline.width
        height: 48
        z: 4

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 21
            anchors.rightMargin: MichiSpacing.lg
            spacing: MichiSpacing.md

            Rectangle {
                Layout.preferredWidth: 14
                Layout.preferredHeight: 14
                radius: 7
                color: MichiPalette.auroraCyan
                border.width: 2
                border.color: MichiPalette.obsidian
            }

            MichiText {
                text: {
                    if (albumTimeline.groupByDecade) {
                        return (section === "Unknown era" || section === "0" || section === "")
                            ? "Unknown date" : section
                    } else {
                        var y = parseInt(section, 10)
                        return (!isNaN(y) && y > 0) ? String(y) : "Unknown date"
                    }
                }
                role: "section"
                font.weight: Font.Bold
                color: MichiPalette.textPrimary
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: MichiSemanticColors.borderSubtle
            }

            MichiText {
                text: albumTimeline.groupByDecade ? "DECADE" : "YEAR"
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
        }
    }

    delegate: Item {
        id: timelineRow
        required property int index
        required property var modelData
        property var album: modelData
        readonly property bool selected: ListView.isCurrentItem
        width: albumTimeline.width
        height: MichiThemeState.density === "compact" ? 58
            : MichiThemeState.density === "comfortable" ? 82 : 70
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: modelData.title + " by " + modelData.artist

        Rectangle {
            anchors.fill: parent
            radius: MichiRadius.md
            color: timelineRow.selected ? MichiSemanticColors.surfaceSelected
                : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
            border.width: timelineRow.selected || hover.hovered ? 1 : 0
            border.color: timelineRow.selected
                ? MichiSemanticColors.auroraBorderSubtle
                : MichiSemanticColors.borderSubtle
            MichiFocusRing {
                visualFocus: timelineRow.activeFocus
                    && MichiAccessibility.keyboardMode
            }
        }

        Rectangle {
            id: timelineLine
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.leftMargin: 27
            width: 1
            color: MichiSemanticColors.borderStrong
        }
        Rectangle {
            anchors.centerIn: timelineLine
            width: timelineRow.selected ? 10 : 8
            height: width
            radius: width / 2
            color: timelineRow.selected
                ? MichiPalette.auroraCyan : MichiPalette.textMuted
            border.width: 2
            border.color: MichiPalette.obsidian
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 48
            anchors.rightMargin: MichiSpacing.lg
            spacing: MichiSpacing.md
            Artwork {
                Layout.preferredWidth: timelineRow.height - MichiSpacing.md
                Layout.preferredHeight: Layout.preferredWidth
                sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
                fallbackText: modelData.title
                requestedSize: Math.round(width * Screen.devicePixelRatio)
                radius: MichiRadius.sm
            }
            ColumnLayout {
                Layout.preferredWidth: Math.min(380, timelineRow.width * 0.35)
                spacing: MichiSpacing.xxs
                MichiText {
                    Layout.fillWidth: true
                    text: modelData.title
                    role: "body"
                    font.weight: timelineRow.selected ? Font.DemiBold : Font.Medium
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: modelData.artist
                    role: "secondary"
                    elide: Text.ElideRight
                }
            }
            MichiText {
                text: modelData.year > 0 ? String(modelData.year) : "—"
                role: "technical"
                technical: true
                color: modelData.year > 0
                    ? MichiPalette.auroraCyan : MichiPalette.textMuted
            }
            MichiText {
                visible: modelData.trackCount > 0
                text: modelData.trackCount + (modelData.trackCount === 1 ? " track" : " tracks")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            Item { Layout.fillWidth: true }
            MichiText {
                visible: modelData.technicalSummary ? (modelData.technicalSummary.length > 0) : false
                text: modelData.technicalSummary || ""
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
        }

        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler {
            onTapped: {
                albumTimeline.currentIndex = timelineRow.index
                timelineRow.forceActiveFocus()
                library.select_album(modelData.key)
            }
        }
        Keys.onReturnPressed: library.select_album(modelData.key)
        Keys.onEnterPressed: library.select_album(modelData.key)
    }
}
