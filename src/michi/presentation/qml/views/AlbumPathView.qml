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
    property var browseState: null
    property string visibleAlbums: "auto"
    property string depthMode: "standard"
    property bool ambientColor: true
    property string metadataLevel: "standard"
    property var cachedKnowledge: ({})
    property bool hasCachedKnowledge: false
    property string cachedAlbumKey: ""
    readonly property real coverSize: Math.max(176, Math.min(330,
        Math.min(width * 0.24 * albumZoom,
            Math.max(176, height - 156))))
    readonly property var currentAlbum: count > 0 && currentIndex >= 0
        ? albumModel[Math.min(currentIndex, albumModel.length - 1)] : null
    AlbumPaletteBinding { id: currentPalette; album: albumsPath.currentAlbum }

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    clip: true
    interactive: count > 1
    pathItemCount: visibleAlbums === "auto"
        ? (MichiBreakpoints.isXl(width) ? 9
            : MichiBreakpoints.isWide(width) ? 7
            : MichiBreakpoints.isMedium(width) ? 5 : 3)
        : Number(visibleAlbums)
    cacheItemCount: pathItemCount + 2
    preferredHighlightBegin: 0.5
    preferredHighlightEnd: 0.5
    highlightRangeMode: PathView.StrictlyEnforceRange
    snapMode: PathView.SnapToItem
    activeFocusOnTab: true
    focus: true
    Accessible.role: Accessible.List
    Accessible.name: qsTr("Albums in album flow view")
    Accessible.description: qsTr("Use Left and Right to browse and Enter to open")

    Component.onCompleted: if (browseState) {
        var restoredIndex = browseState.flowIndex
        if (browseState.currentKey) {
            for (var i = 0; i < albumModel.length; ++i) {
                if (albumModel[i].key === browseState.currentKey) {
                    restoredIndex = i
                    break
                }
            }
        }
        currentIndex = restoredIndex
    }
    onCurrentIndexChanged: if (browseState) {
        browseState.flowIndex = currentIndex
        if (currentAlbum)
            browseState.remember(currentAlbum.key)
    }

    Rectangle {
        anchors.fill: parent
        z: -100
        visible: albumsPath.ambientColor
        color: currentPalette.value.dominant
            || MichiSemanticColors.auroraCyanSurface
        opacity: 0.34
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.paletteCrossfade }
        }
    }

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
        AlbumPaletteBinding { album: pathAlbum.album }
        width: albumsPath.coverSize
        height: albumsPath.coverSize + 48
        scale: PathView.isCurrentItem ? 1.0
            : (PathView.itemScale || 0.58)
                * (albumsPath.depthMode === "subtle" ? 1.08
                    : albumsPath.depthMode === "immersive" ? 0.9 : 1.0)
        opacity: PathView.itemOpacity === undefined ? 1 : PathView.itemOpacity
        z: PathView.isCurrentItem ? 100 : Math.round(PathView.itemDepth || 0)
        Accessible.role: Accessible.Button
        Accessible.name: modelData.title + " by " + modelData.artist
        Accessible.selected: PathView.isCurrentItem
        Accessible.description: PathView.isCurrentItem
            ? "Selected album. Enter to open" : "Select album"

        Rectangle {
            anchors.fill: artwork
            anchors.margins: -MichiSpacing.xs
            radius: MichiRadius.lg
            color: "transparent"
            border.width: PathView.isCurrentItem ? 2 : 1
            // Single accent in the focal area: cyan matches the selection
            // card and its track-count label below (was auroraBlue, which
            // fought the cyan card).
            border.color: tap.pressed ? MichiPalette.auroraCyan
                : PathView.isCurrentItem
                    ? MichiPalette.auroraCyan : MichiSemanticColors.borderSubtle
            opacity: PathView.isCurrentItem || hover.hovered || tap.pressed ? 1 : 0.55
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

        MichiFocusRing {
            anchors.fill: artwork
            visualFocus: (pathAlbum.activeFocus
                || (albumsPath.activeFocus && PathView.isCurrentItem))
                && MichiAccessibility.keyboardMode
        }

        // Ground reflection / floor shadow under cover
        Rectangle {
            anchors.top: artwork.bottom
            anchors.horizontalCenter: artwork.horizontalCenter
            anchors.topMargin: 4
            width: albumsPath.coverSize * 0.88
            height: 10
            radius: 5
            color: MichiSemanticColors.glassShadowFar
            opacity: PathView.isCurrentItem ? 0.75 : 0.35
            z: -1
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
        // TapHandler (not MouseArea): it claims only the tap, leaving the
        // PathView drag/flick intact when the gesture starts on a cover.
        // Click selects + keeps keyboard focus; double-click opens.
        TapHandler {
            id: tap
            exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap
            onSingleTapped: {
                albumsPath.currentIndex = pathAlbum.index
                pathAlbum.forceActiveFocus()
            }
            onDoubleTapped: library.select_album(modelData.key)
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
        height: albumsPath.metadataLevel === "detailed" ? 104
            : albumsPath.metadataLevel === "minimal" ? 64 : 82
        elevation: "elevated"
        contentPadding: MichiSpacing.md
        accented: true
        accentColor: currentPalette.value.accentSafe || MichiPalette.auroraCyan
        materialRole: MichiMaterialRole.elevated
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
                visible: albumsPath.metadataLevel !== "minimal"
                text: albumsPath.currentAlbum
                    ? albumsPath.currentAlbum.trackCount
                        + (albumsPath.currentAlbum.trackCount === 1 ? " track" : " tracks")
                    : ""
                role: "technical"
                technical: true
                color: detailSurface.accentColor
            }
            MichiText {
                visible: albumsPath.metadataLevel === "detailed"
                    && albumsPath.currentAlbum
                    && albumsPath.currentAlbum.technicalSummary.length > 0
                text: albumsPath.currentAlbum
                    ? albumsPath.currentAlbum.technicalSummary : ""
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            MichiText {
                visible: albumsPath.metadataLevel !== "minimal"
                    && albumsPath.hasCachedKnowledge
                    && albumsPath.currentAlbum
                    && albumsPath.cachedAlbumKey === albumsPath.currentAlbum.key
                text: albumsPath.cachedKnowledge
                    ? [albumsPath.cachedKnowledge.label || "",
                        albumsPath.cachedKnowledge.genres
                            ? albumsPath.cachedKnowledge.genres.join(" · ") : ""]
                        .filter(value => value !== "").join(" — ") : ""
                role: "caption"
                Layout.maximumWidth: 180
                color: MichiPalette.textMuted
                elide: Text.ElideRight
            }
            Rectangle {
                Layout.preferredWidth: 1
                Layout.preferredHeight: 30
                color: MichiSemanticColors.borderSubtle
            }
            MichiIconButton {
                Layout.preferredWidth: MichiMetrics.controlMedium
                Layout.preferredHeight: MichiMetrics.controlMedium
                iconName: "chevron-left"
                accessibleName: qsTr("Previous album")
                enabled: albumsPath.count > 1
                onClicked: albumsPath.decrementCurrentIndex()
            }
            MichiIconButton {
                Layout.preferredWidth: MichiMetrics.controlMedium
                Layout.preferredHeight: MichiMetrics.controlMedium
                iconName: "chevron-right"
                accessibleName: qsTr("Next album")
                enabled: albumsPath.count > 1
                onClicked: albumsPath.incrementCurrentIndex()
            }
            MichiButton {
                text: qsTr("Play")
                iconName: "play"
                variant: "primary"
                accessibleName: qsTr("Play selected album")
                onClicked: {
                    if (albumsPath.currentAlbum) {
                        library.play_album(albumsPath.currentAlbum.key)
                    }
                }
            }
            MichiButton {
                text: qsTr("Open album")
                iconName: "album"
                variant: "secondary"
                accessibleName: qsTr("Open selected album")
                onClicked: {
                    if (albumsPath.currentAlbum)
                        library.select_album(albumsPath.currentAlbum.key)
                }
            }
        }
    }
}
