import QtQuick
import "."

/* Michi Visual Quality — global effect controller
 *
 * Profiles:
 *   low:       no shaders, no textures, reduced animations
 *   balanced:  blue-noise microtexture, limited effects (DEFAULT)
 *   premium:   full effects, additional glow layers
 *
 * All profiles preserve full UI functionality.
 * reducedMotion disables temporal animation regardless of profile.
 */

pragma Singleton
Item {
    id: root

    property string profile: "balanced"
    property bool textureEnabled: profile !== "low"
    property bool glowEnabled: profile === "premium"
    property bool blurEnabled: false
    property real animationScale: {
        const profileScale = profile === "low" ? 0.5 : 1.0
        if (typeof visualQuality !== "undefined" && visualQuality)
            return visualQuality.animationScale * profileScale
        return profileScale
    }

    function setProfile(p) {
        if (["low", "balanced", "premium"].indexOf(p) >= 0)
            root.profile = p
    }
}
