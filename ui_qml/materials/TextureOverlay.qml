import QtQuick
import "../theme"

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
                : "../assets/textures/michi-grain.svg"
        fillMode: root.variant === "contours" ? Image.PreserveAspectCrop : Image.Tile
        sourceSize.width: root.variant === "contours"
                          ? Math.max(640, root.width)
                          : MichiTheme.textureTileSize
        sourceSize.height: root.variant === "contours"
                           ? Math.max(320, root.height)
                           : MichiTheme.textureTileSize
        opacity: root.strength * (root.variant === "contours"
                                  ? (MichiTheme.darkMode ? 0.30 : 0.18)
                                  : (MichiTheme.darkMode ? 0.20 : 0.12))
        smooth: true
        mipmap: root.variant === "contours"
    }
}
