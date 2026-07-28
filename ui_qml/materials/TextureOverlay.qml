import QtQuick
import "../theme"

/* Michi Music Player — Texture Overlay
 * 
 * Texture system for subtle surface depth.
 * - grain: replaced by blue-noise overlay (see BlueNoiseOverlay.qml)
 * - contours: decorative SVG curves, restricted to hero surfaces only
 *
 * Blue-noise tile approach replaces the periodic SVG grain pattern
 * that produced visible seams and banding at 96px intervals.
 */

Item {
    id: root

    property string variant: "grain"
    property real strength: 1.0

    enabled: false
    Accessible.ignored: true

    Image {
        anchors.fill: parent
        source: root.variant === "contours"
                ? "../assets/textures/michi-contours.svg"
                : ""  /* grain variant replaced by BlueNoiseOverlay */
        fillMode: root.variant === "contours" ? Image.PreserveAspectCrop : Image.Tile
        sourceSize.width: root.variant === "contours"
                          ? Math.max(640, root.width)
                          : 64
        sourceSize.height: root.variant === "contours"
                           ? Math.max(320, root.height)
                           : 64
        opacity: root.variant === "contours"
                 ? root.strength * (MichiTheme.darkMode ? 0.15 : 0.10)
                 : 0.0
        smooth: false
        mipmap: root.variant === "contours"
    }
}
