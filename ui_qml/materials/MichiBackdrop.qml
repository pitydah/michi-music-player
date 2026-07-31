import QtQuick
import "../theme"

/* Michi Music Player — Single Global Backdrop
 *
 * A single backdrop instance shared by the entire shell.
 * Combines:
 *   - Solid base canvas (bgApp)
 *   - Primary radial glow (accent top-center)
 *   - Secondary radial glow (accent bottom-right, subtle)
 *   - Vignette (dark edges)
 *   - Blue-noise microtexture (almost imperceptible)
 *
 * This replaces per-page AcrylicBackdrop instances.
 * One backdrop. One surface. One system.
 */

Item {
    id: root
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp

        // Primary glow — top-center accent wash
        Rectangle {
            width: Math.min(parent.width * 1.2, 800)
            height: Math.min(parent.height * 0.6, 500)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: -height * 0.3
            radius: width * 0.5
            gradient: Gradient {
                GradientStop { position: 0.0; color: MichiTheme.colors.accentGlow }
                GradientStop { position: 0.5; color: Qt.alpha(MichiTheme.colors.accentPrimary, 0.03) }
                GradientStop { position: 1.0; color: Qt.alpha(MichiTheme.colors.accentPrimary, 0.0) }
            }
        }

        // Secondary glow — bottom-right accent hint
        Rectangle {
            width: Math.min(parent.width * 0.6, 500)
            height: Math.min(parent.height * 0.4, 400)
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: -width * 0.2
            anchors.bottomMargin: -height * 0.2
            radius: width * 0.5
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.alpha(MichiTheme.colors.accentPrimary, 0.04) }
                GradientStop { position: 1.0; color: Qt.alpha(MichiTheme.colors.accentPrimary, 0.0) }
            }
        }

        // Vignette — dark bottom edge
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: parent.height * 0.5
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: Qt.alpha(MichiTheme.colors.overlayDark, 0.45) }
            }
        }
    }

    // Blue-noise microtexture
    BlueNoiseOverlay {
        anchors.fill: parent
    }
}
