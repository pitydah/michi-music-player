import QtQuick
import "../theme"

/* MichiArtworkGlow — soft glow behind artwork. */
Item {
    id: root
    property color glowColor: MichiTheme.colors.accentWarmViolet
    property real glowStrength: 0.25

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: root.glowColor
        opacity: root.glowStrength
        scale: 0.9
    }
}
