import QtQuick
import "../primitives"
import "../theme"

// One hero-only renderer: no per-card shader or blur. User colors/images
// are always neutralized by the semantic scrim and bottom transition.
Item {
    id: root

    property string heroMode: "auto"
    property color solidColor: MichiPalette.playlistHeroTop
    property var gradientColors: [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid]
    property real gradientAngle: 135
    property string heroImagePath: ""
    property string coverPath: ""
    property var mosaicArtworkPaths: []
    property var autoColors: [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid, MichiPalette.playlistHeroBottom]

    readonly property string autoArtworkPath: root.coverPath.length > 0
        ? root.coverPath
        : root.mosaicArtworkPaths && root.mosaicArtworkPaths.length > 0
            ? root.mosaicArtworkPaths[0] : ""
    readonly property real readingScrimOpacity:
        root.heroMode === "image" || root.heroMode === "solid" ? 0.88 : 0.64

    Rectangle {
        anchors.fill: parent
        color: root.heroMode === "solid" ? root.solidColor : MichiPalette.obsidianDeep
    }

    Canvas {
        id: gradientCanvas
        anchors.fill: parent
        visible: root.heroMode === "auto" || root.heroMode === "gradient"
        renderTarget: Canvas.Image

        function repaint() { requestPaint() }
        onWidthChanged: repaint()
        onHeightChanged: repaint()
        Connections {
            target: root
            function onHeroModeChanged() { gradientCanvas.repaint() }
            function onGradientColorsChanged() { gradientCanvas.repaint() }
            function onGradientAngleChanged() { gradientCanvas.repaint() }
            function onAutoColorsChanged() { gradientCanvas.repaint() }
        }
        onPaint: {
            var context = getContext("2d")
            context.clearRect(0, 0, width, height)
            var colors = root.heroMode === "auto" ? root.autoColors : root.gradientColors
            if (!colors || colors.length < 2)
                colors = [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid]
            var radians = root.gradientAngle * Math.PI / 180
            var dx = Math.cos(radians)
            var dy = Math.sin(radians)
            var span = Math.abs(width * dx) + Math.abs(height * dy)
            var cx = width / 2
            var cy = height / 2
            var gradient = context.createLinearGradient(
                cx - dx * span / 2, cy - dy * span / 2,
                cx + dx * span / 2, cy + dy * span / 2)
            for (var index = 0; index < colors.length; ++index)
                gradient.addColorStop(index / (colors.length - 1), colors[index])
            context.fillStyle = gradient
            context.fillRect(0, 0, width, height)
        }
    }

    Image {
        anchors.fill: parent
        visible: root.heroMode === "auto" && root.autoArtworkPath.length > 0
        source: visible ? Qt.resolvedUrl(root.autoArtworkPath) : ""
        sourceSize.width: Math.min(1600, Math.round(width * Screen.devicePixelRatio))
        sourceSize.height: Math.min(600, Math.round(height * Screen.devicePixelRatio))
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectCrop
        opacity: 0.28
    }

    Image {
        anchors.fill: parent
        visible: root.heroMode === "image" && root.heroImagePath.length > 0
        source: visible ? Qt.resolvedUrl(root.heroImagePath) : ""
        sourceSize.width: Math.min(1600, Math.round(width * Screen.devicePixelRatio))
        sourceSize.height: Math.min(600, Math.round(height * Screen.devicePixelRatio))
        asynchronous: true
        // Managed hero files are mutable at a stable path. Caching would
        // keep the previous bytes visible after a same-extension replace.
        cache: false
        fillMode: Image.PreserveAspectCrop
    }

    // A horizontal editorial scrim reserves a reliably calm reading field
    // at the left without flattening the user's artwork on the right.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: MichiSemanticColors.scrimStrong }
            GradientStop { position: 0.46; color: MichiSemanticColors.scrim }
            GradientStop { position: 0.78; color: MichiSemanticColors.playlistHeroBottomScrim }
            GradientStop { position: 1; color: MichiSemanticColors.borderSubtle }
        }
        opacity: root.readingScrimOpacity
    }

    Rectangle {
        anchors.fill: parent
        color: MichiPalette.obsidianDeep
        opacity: root.heroMode === "image" ? 0.12 : 0.06
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 0.62; color: MichiSemanticColors.playlistHeroBottomScrim }
            GradientStop { position: 1; color: MichiPalette.obsidian }
        }
    }

    // A single low-energy contour gives generated/solid heroes a little
    // musical cadence. It stays out of custom images and remains below 6%
    // effective opacity, so it reads as material rather than decoration.
    Canvas {
        id: signalContour
        anchors.fill: parent
        visible: root.heroMode !== "image" && width >= 720
        opacity: 0.28
        renderTarget: Canvas.Image
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var context = getContext("2d")
            context.clearRect(0, 0, width, height)
            context.beginPath()
            context.moveTo(width * 0.52, height * 0.32)
            context.bezierCurveTo(
                width * 0.64, height * 0.20,
                width * 0.74, height * 0.44,
                width * 0.84, height * 0.30)
            context.bezierCurveTo(
                width * 0.89, height * 0.23,
                width * 0.93, height * 0.28,
                width * 0.97, height * 0.24)
            context.strokeStyle = MichiSemanticColors.auroraCyanBorderSubtle
            context.lineWidth = 1
            context.stroke()
        }
        Component.onCompleted: requestPaint()
    }

    // One inexpensive texture per hero prevents large flat gradients from
    // reading as unfinished while preserving the no-per-card-effects rule.
    MichiMaterialTexture {
        anchors.fill: parent
        tileSeed: 222
        textureOpacity: Math.min(0.10,
            MichiThemeState.glassQuality === "low" ? 0 : 0.10)
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: MichiSemanticColors.innerHighlight
        opacity: 0.7
    }
}
