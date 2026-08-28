import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

GridView {
    id: albumVinyl
    objectName: "albumVinylView"

    property var albumModel: library.albums
    property real albumZoom: 1.0
    readonly property int minimumTileWidth: MichiThemeState.density === "compact"
        ? Math.round(164 * albumZoom)
        : MichiThemeState.density === "comfortable"
            ? Math.round(236 * albumZoom) : Math.round(198 * albumZoom)
    readonly property int columnCount: Math.max(1, Math.floor(width / minimumTileWidth))

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    cellWidth: width / columnCount
    cellHeight: Math.min(348, Math.max(190,
        cellWidth + Math.round(42 * albumZoom)))
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    cacheBuffer: cellHeight * 2
    Accessible.role: Accessible.List
    Accessible.name: qsTr("Albums on the vinyl wall")
    Accessible.description: qsTr("Use arrow keys to browse and Enter to open")

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }

    ScrollBar.vertical: MichiScrollBar { }

    delegate: Item {
        id: vinylTile
        required property int index
        required property var modelData
        property var album: modelData
        readonly property bool selected: GridView.isCurrentItem
        readonly property real stageSize: Math.min(width - MichiSpacing.xl,
            height - 76)
        readonly property real sleeveSize: stageSize * 0.76
        width: albumVinyl.cellWidth - MichiThemeState.contentGap
        height: albumVinyl.cellHeight - MichiThemeState.contentGap
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: modelData.title + " by " + modelData.artist
        Accessible.selected: vinylTile.selected
        Accessible.description: qsTr("Open album")

        Rectangle {
            anchors.fill: parent
            radius: MichiRadius.lg
            color: vinylTile.selected ? MichiSemanticColors.surfaceSelected
                : hover.hovered ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
            border.width: 1
            border.color: vinylTile.selected
                ? MichiPalette.auroraCyan : hover.hovered ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
            MichiFocusRing {
                visualFocus: vinylTile.activeFocus
                    && MichiAccessibility.keyboardMode
            }
        }

        Item {
            id: stage
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: MichiSpacing.sm
            width: vinylTile.stageSize
            height: vinylTile.stageSize

            Rectangle {
                id: vinylDisc
                width: vinylTile.sleeveSize
                height: width
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: hover.hovered || vinylTile.selected
                    ? width * 0.16 : width * 0.04
                color: MichiPalette.graphiteRaised
                border.width: 1
                border.color: MichiSemanticColors.borderStrong

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: width / 2
                    color: "transparent"
                    border.width: 1
                    border.color: MichiSemanticColors.innerHighlight
                    opacity: 0.5
                }

                Repeater {
                    model: 3
                    Rectangle {
                        anchors.centerIn: parent
                        width: vinylDisc.width - MichiSpacing.md - index * vinylDisc.width * 0.18
                        height: width
                        radius: width / 2
                        color: "transparent"
                        border.width: 1
                        border.color: MichiSemanticColors.borderSubtle
                        opacity: 0.7
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.32
                    height: width
                    radius: width / 2
                    color: vinylTile.selected
                        ? MichiPalette.auroraCyan : MichiPalette.graphiteRaised
                    border.width: 1
                    border.color: MichiSemanticColors.innerHighlight
                    Rectangle {
                        anchors.centerIn: parent
                        width: MichiSpacing.xs
                        height: width
                        radius: width / 2
                        color: MichiPalette.obsidian
                    }
                }

                Behavior on anchors.horizontalCenterOffset {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation {
                        duration: MichiMotion.artwork
                        easing.type: MichiMotion.outCubic
                    }
                }
            }

            Artwork {
                id: sleeve
                width: vinylTile.sleeveSize
                height: width
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: -width * 0.06
                z: 2
                sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
                fallbackText: modelData.title
                requestedSize: Math.round(width * Screen.devicePixelRatio)
            }
        }

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: stage.bottom
            anchors.leftMargin: MichiSpacing.sm
            anchors.rightMargin: MichiSpacing.sm
            spacing: MichiSpacing.xxs
            MichiText {
                Layout.fillWidth: true
                text: modelData.title
                role: "body"
                font.weight: vinylTile.selected ? Font.DemiBold : Font.Medium
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }
            MichiText {
                Layout.fillWidth: true
                text: modelData.technicalSummary || (modelData.trackCount
                    + (modelData.trackCount === 1 ? " track" : " tracks"))
                role: "technical"
                technical: true
                color: vinylTile.selected
                    ? MichiPalette.auroraCyan : MichiPalette.textMuted
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }
            MichiText {
                Layout.fillWidth: true
                text: modelData.artist + (modelData.year > 0
                    ? " · " + modelData.year : "")
                role: "secondary"
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }
        }

        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler {
            id: vinylTap
            // First tap selects (showing the rich selected state: disc
            // offset, cyan label); tapping the already-selected tile opens.
            onTapped: {
                var wasCurrent = albumVinyl.currentIndex === vinylTile.index
                albumVinyl.currentIndex = vinylTile.index
                vinylTile.forceActiveFocus()
                if (wasCurrent)
                    library.select_album(modelData.key)
            }
        }
        AlbumContextArea { anchors.fill: parent; album: modelData }
        Keys.onReturnPressed: library.select_album(modelData.key)
        Keys.onEnterPressed: library.select_album(modelData.key)
    }
}
