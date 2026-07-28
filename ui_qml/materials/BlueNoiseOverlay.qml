import QtQuick
import "../theme"

Item {
    id: root
    anchors.fill: parent
    visible: true

    Image {
        anchors.fill: parent
        source: "../assets/textures/blue-noise-64.png"
        fillMode: Image.Tile
        smooth: false
        mipmap: false
        opacity: 0.025
    }
}
