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
    property var browseState: null
    property string spacingMode: "standard"
    property string revealMode: "standard"
    property string metadataLevel: "standard"
    property bool artworkLabel: true
    MichiMaterial {
        id: vinylMaterial
        role: MichiMaterialRole.vinyl
    }
    Rectangle {
        x: albumVinyl.contentX
        y: albumVinyl.contentY
        width: albumVinyl.width
        height: albumVinyl.height
        color: vinylMaterial.baseColor
        z: -2
    }
    MichiMaterialTexture {
        x: albumVinyl.contentX
        y: albumVinyl.contentY
        width: albumVinyl.width
        height: albumVinyl.height
        textureName: vinylMaterial.textureName
        textureOpacity: vinylMaterial.textureOpacity
        z: -1
    }
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

    Component.onCompleted: if (browseState) Qt.callLater(function() {
        var restoredIndex = browseState.vinylIndex
        if (browseState.currentKey) {
            for (var i = 0; i < albumModel.length; ++i) {
                if (albumModel[i].key === browseState.currentKey) {
                    restoredIndex = i
                    break
                }
            }
        }
        albumVinyl.currentIndex = restoredIndex
        albumVinyl.contentY = browseState.vinylContentY
    })
    onContentYChanged: if (browseState) browseState.vinylContentY = contentY
    onCurrentIndexChanged: if (browseState) {
        browseState.vinylIndex = currentIndex
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            browseState.remember(albumModel[currentIndex].key)
    }

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
        readonly property int wallGap: albumVinyl.spacingMode === "tight"
            ? MichiSpacing.sm : albumVinyl.spacingMode === "gallery"
                ? MichiSpacing.xl : MichiThemeState.contentGap
        width: albumVinyl.cellWidth - wallGap
        height: albumVinyl.cellHeight - wallGap
        activeFocusOnTab: false
        Accessible.role: Accessible.Button
        Accessible.name: modelData.title + " by " + modelData.artist
        Accessible.selected: vinylTile.selected
        Accessible.description: qsTr("Open album")

        Rectangle {
            anchors.fill: parent
            radius: MichiRadius.lg
            color: vinylTile.selected ? MichiSemanticColors.surfaceSelected
                : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
            border.width: 1
            border.color: vinylTile.selected
                ? (modelData.artworkPalette
                    ? modelData.artworkPalette.accentSafe : MichiPalette.auroraCyan)
                : hover.hovered ? MichiSemanticColors.borderStrong : "transparent"
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

            MichiVinylDisc {
                id: vinylDisc
                width: vinylTile.sleeveSize
                height: width
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: hover.hovered || vinylTile.selected
                    ? width * (albumVinyl.revealMode === "subtle" ? 0.1
                        : albumVinyl.revealMode === "pronounced" ? 0.24 : 0.16)
                    : width * 0.04
                selected: vinylTile.selected
                labelColor: albumVinyl.artworkLabel && modelData.artworkPalette
                    ? modelData.artworkPalette.accentSafe : MichiPalette.graphite
                rotation: vinylTile.selected ? 1.5 : hover.hovered ? 0.8 : 0

                Behavior on anchors.horizontalCenterOffset {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation {
                        duration: MichiMotion.vinylReveal
                        easing.type: MichiMotion.outCubic
                    }
                }
                Behavior on rotation {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation {
                        duration: MichiMotion.vinylReveal
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
            Rectangle {
                anchors.top: sleeve.top
                anchors.bottom: sleeve.bottom
                anchors.right: sleeve.right
                width: 3
                color: MichiSemanticColors.innerHighlight
                opacity: 0.34
                z: 3
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
                visible: albumVinyl.metadataLevel !== "minimal"
                text: modelData.technicalSummary || (modelData.trackCount
                    + (modelData.trackCount === 1 ? " track" : " tracks"))
                role: "technical"
                technical: true
                color: vinylTile.selected
                    ? (modelData.artworkPalette
                        ? modelData.artworkPalette.accentSafe : MichiPalette.auroraCyan)
                    : MichiPalette.textMuted
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }
            MichiText {
                Layout.fillWidth: true
                visible: albumVinyl.metadataLevel === "detailed"
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
            exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap
            onSingleTapped: {
                albumVinyl.currentIndex = vinylTile.index
                vinylTile.forceActiveFocus()
            }
            onDoubleTapped: library.select_album(modelData.key)
        }
        Keys.onReturnPressed: library.select_album(modelData.key)
        Keys.onEnterPressed: library.select_album(modelData.key)
    }
}
