import QtQuick
import "../theme"

Image {
    id: root

    // Per-surface seed de-synchronizes the tile alignment between adjacent
    // surfaces so the grain never reads as one shared pattern.
    property int tileSeed: 0

    // Dense film grain: dots are internally 5-22% opaque, so the tile
    // opacity lands each dot at ~1-5% (standard) / ~2-8% (high) on screen —
    // perceptible as material, never as noise. Negative values fall back
    // to the quality-based default (surfaces may pass -1 from the glass).
    property real textureOpacity: -1

    sourceSize.width: 128
    sourceSize.height: 128
    fillMode: Image.Tile
    asynchronous: true
    cache: true
    smooth: true
    mipmap: false
    opacity: root.textureOpacity >= 0 ? root.textureOpacity
        : MichiThemeState.glassQuality === "high" ? 0.36
        : MichiThemeState.glassQuality === "low" ? 0 : 0.22
    visible: opacity > 0
    Accessible.ignored: true

    // Deterministic procedural grain tile (128px). Replaces the old 64px
    // SVG: 18 isolated sub-pixel dots made the texture mathematically
    // invisible (0.28% coverage) and aliased hard at every tile seam.
    // This tile holds ~260 gaussian dots (~5% coverage), renders smooth
    // anti-aliased circles and never shows a repeating lattice.
    Canvas {
        id: grainCanvas
        width: 128
        height: 128
        visible: false

        // mulberry32 — deterministic PRNG driven by the surface seed
        function makeRandom(seed) {
            var a = seed >>> 0
            return function() {
                a |= 0
                a = a + 0x6D2B79F5 | 0
                var t = Math.imul(a ^ a >>> 15, 1 | a)
                t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t
                return ((t ^ t >>> 14) >>> 0) / 4294967296
            }
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var rng = root.makeRandom(0x9E3779B9 ^ root.tileSeed)
            for (var i = 0; i < 260; i++) {
                var x = rng() * width
                var y = rng() * height
                // sum-of-uniforms approximates a bell curve for radii
                var g = (rng() + rng()) * 0.5
                var radius = 0.45 + g * 1.15   // 0.45..1.60 px
                var alpha = 0.05 + rng() * 0.17 // 5..22 %
                ctx.beginPath()
                ctx.arc(x, y, radius, 0, Math.PI * 2)
                ctx.fillStyle = "rgba(255,255,255," + alpha.toFixed(3) + ")"
                ctx.fill()
            }
            root.source = grainCanvas.toDataURL("image/png")
        }

        Component.onCompleted: requestPaint()
    }

    onTileSeedChanged: grainCanvas.requestPaint()
}