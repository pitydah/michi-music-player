import QtQuick
import "../theme"

Image {
    id: root

    property real textureOpacity: MichiThemeState.glassQuality === "high" ? 0.16
        : MichiThemeState.glassQuality === "low" ? 0 : 0.09

    source: "../assets/michi-grain.svg"
    sourceSize.width: 64
    sourceSize.height: 64
    fillMode: Image.Tile
    asynchronous: true
    cache: true
    smooth: false
    mipmap: false
    opacity: textureOpacity
    visible: opacity > 0
    Accessible.ignored: true
}
