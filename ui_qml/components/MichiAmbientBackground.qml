import QtQuick
import "../theme"
import "../materials"

/* MichiAmbientBackground — subtle ambient gradient background.
 * Three layers: solid base, radial ambient glow, fine grain.
 * Never affects legibility. Respects reducedMotion.
 */
Item {
    id: root
    anchors.fill: parent

    property color baseColor: MichiTheme.colors.bgCanvas
    property color ambientColor: MichiTheme.colors.accentGlowSubtle

    Rectangle {
        anchors.fill: parent
        color: root.baseColor
    }

    // Ambient radial glow
    Rectangle {
        width: Math.min(parent.width * 1.1, 900)
        height: Math.min(parent.height * 0.8, 600)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: -height * 0.25
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.ambientColor }
            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0) }
        }
        opacity: 0.5
    }

    // Fine grain (subtle, tileable)
    BlueNoiseOverlay {
        anchors.fill: parent
        opacity: 0.02
    }
}
