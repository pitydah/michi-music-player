import QtQuick
import "../theme"

Item {
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

    /* Preserve the original component contract: consumers historically use
     * `opacity > 0` as the material-presence predicate.  The root changed
     * from Image to Item only so decode/loading failure can be isolated; its
     * observable opacity/visibility semantics must remain identical. */
    opacity: root.textureOpacity
    visible: opacity > 0
    implicitWidth: 128
    implicitHeight: 128

    readonly property bool textureReady: texture.status === Image.Ready

    Image {
        id: texture
        anchors.fill: parent
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

        // Loading/Error never paints Qt's broken-image placeholder.  The
        // parent keeps the historical material opacity; this child is either
        // fully present after a successful decode or visually absent.
        opacity: root.textureReady ? 1 : 0
        visible: root.textureReady
        Accessible.ignored: true
    }

    Accessible.ignored: true

    // Static repository assets are decoded once by Qt's image cache and
    // shared by every surface. No Canvas or data URL is created per item.
}
