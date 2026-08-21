import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
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
    Accessible.name: "Albums on the vinyl wall"
    Accessible.description: "Use arrow keys to browse and Enter to open"

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
        Accessible.description: "Open album"

        Rectangle {
            anchors.fill: parent
            radius: MichiRadius.lg
            color: vinylTile.selected ? MichiSemanticColors.surfaceSelected
                : hover.hovered ? MichiSemanticColors.surfaceHover
                : MichiSemanticColors.controlSurface
            border.width: 1
            border.color: vinylTile.selected
                ? MichiPalette.auroraBlue : hover.hovered
                    ? MichiSemanticColors.borderStrong
                    : MichiSemanticColors.borderSubtle
            Rectangle {
                visible: vinylTile.selected
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: MichiRadius.lg
                anchors.rightMargin: MichiRadius.lg
                height: 2
                radius: 1
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: MichiPalette.auroraBlue }
                    GradientStop { position: 0.55; color: MichiPalette.auroraCyan }
                    GradientStop { position: 1; color: MichiPalette.auroraPurple }
                }
            }
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
                anchors.centerIn: parent
                width: parent.width * 0.88
                height: width
                radius: width / 2
                color: vinylTile.selected
                    ? MichiSemanticColors.auroraCyanSurface : "transparent"
                border.width: vinylTile.selected ? 1 : 0
                border.color: MichiSemanticColors.auroraCyanBorderSubtle
                opacity: vinylTile.selected ? 0.48 : 0
            }

            Rectangle {
                id: vinylDisc
                width: vinylTile.sleeveSize
                height: width
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: hover.hovered || vinylTile.selected
                    ? width * 0.24 : width * 0.15
                color: MichiPalette.graphite
                border.width: 1
                border.color: MichiSemanticColors.borderStrong

                Repeater {
                    model: 4
                    Rectangle {
                        anchors.centerIn: parent
                        width: vinylDisc.width - MichiSpacing.md - index * vinylDisc.width * 0.16
                        height: width
                        radius: width / 2
                        color: "transparent"
                        border.width: 1
                        border.color: MichiSemanticColors.borderSubtle
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.31
                    height: width
                    radius: width / 2
                    color: vinylTile.selected
                        ? MichiPalette.auroraPurple : MichiPalette.smokeRaised
                    border.width: 1
                    border.color: MichiSemanticColors.borderStrong
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
                anchors.horizontalCenterOffset: -width * 0.12
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
            onTapped: {
                albumVinyl.currentIndex = vinylTile.index
                vinylTile.forceActiveFocus()
                library.select_album(modelData.key)
            }
        }
        Keys.onReturnPressed: library.select_album(modelData.key)
        Keys.onEnterPressed: library.select_album(modelData.key)
    }
}
