import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

PathView {
    id: albumsPath
    objectName: "albumCoverView"

    property var albumModel: library.albums
    property real albumZoom: 1.0
    readonly property real coverSize: Math.max(176, Math.min(330,
        Math.min(width * 0.24 * albumZoom,
            Math.max(176, height - 156))))
    readonly property var currentAlbum: count > 0 && currentIndex >= 0
        ? albumModel[Math.min(currentIndex, albumModel.length - 1)] : null

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    clip: true
    interactive: count > 1
    pathItemCount: width >= 1500 ? 9 : width >= 1050 ? 7 : 5
    cacheItemCount: pathItemCount + 2
    preferredHighlightBegin: 0.5
    preferredHighlightEnd: 0.5
    highlightRangeMode: PathView.StrictlyEnforceRange
    snapMode: PathView.SnapToItem
    activeFocusOnTab: true
    focus: true
    Accessible.role: Accessible.List
    Accessible.name: "Albums in PathView"
    Accessible.description: "Use Left and Right to browse and Enter to open"

    Keys.onLeftPressed: decrementCurrentIndex()
    Keys.onRightPressed: incrementCurrentIndex()
    Keys.onReturnPressed: {
        if (currentAlbum)
            library.select_album(currentAlbum.key)
    }
    Keys.onEnterPressed: {
        if (currentAlbum)
            library.select_album(currentAlbum.key)
    }
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Home) {
            currentIndex = count > 0 ? 0 : -1
            event.accepted = true
        } else if (event.key === Qt.Key_End) {
            currentIndex = count > 0 ? count - 1 : -1
            event.accepted = true
        }
    }

    path: Path {
        startX: -albumsPath.coverSize * 0.25
        startY: albumsPath.height * 0.48
        PathAttribute { name: "itemScale"; value: 0.58 }
        PathAttribute { name: "itemOpacity"; value: 0.22 }
        PathAttribute { name: "itemDepth"; value: 0 }

        PathQuad {
            x: albumsPath.width * 0.26
            y: albumsPath.height * 0.43
            controlX: albumsPath.width * 0.12
            controlY: albumsPath.height * 0.46
        }
        PathAttribute { name: "itemScale"; value: 0.76 }
        PathAttribute { name: "itemOpacity"; value: 0.68 }
        PathAttribute { name: "itemDepth"; value: 30 }

        PathQuad {
            x: albumsPath.width * 0.50
            y: albumsPath.height * 0.37
            controlX: albumsPath.width * 0.40
            controlY: albumsPath.height * 0.38
        }
        PathAttribute { name: "itemScale"; value: 1.0 }
        PathAttribute { name: "itemOpacity"; value: 1.0 }
        PathAttribute { name: "itemDepth"; value: 100 }

        PathQuad {
            x: albumsPath.width * 0.74
            y: albumsPath.height * 0.43
            controlX: albumsPath.width * 0.60
            controlY: albumsPath.height * 0.38
        }
        PathAttribute { name: "itemScale"; value: 0.76 }
        PathAttribute { name: "itemOpacity"; value: 0.68 }
        PathAttribute { name: "itemDepth"; value: 30 }

        PathQuad {
            x: albumsPath.width + albumsPath.coverSize * 0.25
            y: albumsPath.height * 0.48
            controlX: albumsPath.width * 0.88
            controlY: albumsPath.height * 0.46
        }
        PathAttribute { name: "itemScale"; value: 0.58 }
        PathAttribute { name: "itemOpacity"; value: 0.22 }
        PathAttribute { name: "itemDepth"; value: 0 }
    }

    delegate: Item {
        id: pathAlbum
        required property int index
        required property var modelData
        property var album: modelData
        width: albumsPath.coverSize
        height: albumsPath.coverSize + 48
        scale: PathView.isCurrentItem ? 1.0 : (PathView.itemScale || 0.58)
        opacity: PathView.itemOpacity === undefined ? 1 : PathView.itemOpacity
        z: PathView.isCurrentItem ? 100 : Math.round(PathView.itemDepth || 0)
        Accessible.role: Accessible.Button
        Accessible.name: modelData.title + " by " + modelData.artist
        Accessible.description: PathView.isCurrentItem
            ? "Selected album. Enter to open" : "Select album"

        Rectangle {
            anchors.fill: artwork
            anchors.margins: -MichiSpacing.xs
            radius: MichiRadius.lg
            color: "transparent"
            border.width: PathView.isCurrentItem ? 2 : 1
            border.color: PathView.isCurrentItem
                ? MichiPalette.auroraBlue : MichiSemanticColors.borderSubtle
            opacity: PathView.isCurrentItem || hover.hovered ? 1 : 0.55
        }

        Artwork {
            id: artwork
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: albumsPath.coverSize
            height: width
            sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
            fallbackText: modelData.title
            requestedSize: Math.round(width * Screen.devicePixelRatio)
        }

        MichiText {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: artwork.bottom
            anchors.topMargin: MichiSpacing.sm
            text: modelData.title
            visible: !PathView.isCurrentItem
            role: "body"
            font.weight: PathView.isCurrentItem ? Font.DemiBold : Font.Medium
            color: PathView.isCurrentItem
                ? MichiPalette.textPrimary : MichiPalette.textSecondary
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: albumsPath.currentIndex = pathAlbum.index
            onDoubleClicked: library.select_album(modelData.key)
        }

        Behavior on scale {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
        }
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.standard }
        }
    }

    MichiGlassSurface {
        id: detailSurface
        objectName: "pathViewSelectionCard"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: MichiSpacing.lg
        width: Math.min(720, parent.width - MichiSpacing.xl * 2)
        height: 76
        elevation: "elevated"
        contentPadding: MichiSpacing.md
        accented: true
        accentColor: MichiPalette.auroraCyan
        visible: albumsPath.currentAlbum !== null
        z: 1000

        RowLayout {
            anchors.fill: parent
            spacing: MichiSpacing.md
            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xxs
                MichiText {
                    Layout.fillWidth: true
                    text: albumsPath.currentAlbum ? albumsPath.currentAlbum.title : ""
                    role: "section"
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: albumsPath.currentAlbum
                        ? albumsPath.currentAlbum.artist + (albumsPath.currentAlbum.year > 0
                            ? " · " + albumsPath.currentAlbum.year : "") : ""
                    role: "secondary"
                    elide: Text.ElideRight
                }
            }
            MichiText {
                text: albumsPath.currentAlbum
                    ? albumsPath.currentAlbum.trackCount
                        + (albumsPath.currentAlbum.trackCount === 1 ? " TRACK" : " TRACKS")
                    : ""
                role: "technical"
                technical: true
                color: MichiPalette.auroraCyan
            }
            Rectangle {
                Layout.preferredWidth: 1
                Layout.preferredHeight: 30
                color: MichiSemanticColors.borderSubtle
            }
            MichiIconButton {
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                iconName: "chevron-left"
                accessibleName: "Previous album"
                enabled: albumsPath.count > 1
                onClicked: albumsPath.decrementCurrentIndex()
            }
            MichiIconButton {
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                iconName: "chevron-right"
                accessibleName: "Next album"
                enabled: albumsPath.count > 1
                onClicked: albumsPath.incrementCurrentIndex()
            }
            MichiButton {
                text: "Open album"
                iconName: "album"
                variant: "secondary"
                accessibleName: "Open selected album"
                onClicked: {
                    if (albumsPath.currentAlbum)
                        library.select_album(albumsPath.currentAlbum.key)
                }
            }
        }

        Behavior on y {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation {
                duration: MichiMotion.standard
                easing.type: MichiMotion.outCubic
            }
        }
    }
}
