import QtQuick
import "../theme"

Image {
    id: root

    // Per-surface seed de-synchronizes the tile alignment between adjacent
    // surfaces so the grain never reads as one shared pattern.
    property int tileSeed: 0
    property string textureName: "grain-graphite-01"

    // Dense film grain: dots are internally 5-22% opaque, so the tile
    // opacity lands each dot at ~1-5% (standard) / ~2-8% (high) on screen —
    // perceptible as material, never as noise.
    property real textureOpacity: MichiThemeState.glassQuality === "high" ? 0.36
        : MichiThemeState.glassQuality === "low" ? 0 : 0.22

    source: {
        var resolved = root.textureName
        if (resolved === "grain-graphite-01" && root.tileSeed % 2 !== 0)
            resolved = "grain-graphite-02"
        return "../assets/" + resolved + ".svg"
    }
    sourceSize.width: 128
    sourceSize.height: 128
    fillMode: Image.Tile
    asynchronous: true
    cache: true
    smooth: true
    mipmap: false
    opacity: textureOpacity
    visible: opacity > 0
    Accessible.ignored: true

    // Static repository assets are decoded once by Qt's image cache and
    // shared by every surface. No Canvas or data URL is created per item.
}
