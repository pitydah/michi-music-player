import QtQuick
import "../theme"

// MichiPeek — brand-specific playlist reveal. It carries no information;
// the card remains fully usable when motion is reduced or imagery is unseen.
Item {
    id: root

    property bool revealed: false
    // The cover occludes most of the body. Only 30–36 px of profile clear
    // its right edge, so the eye never competes with the artwork.
    readonly property real revealDistance: Math.max(30,
        Math.min(36, width * 0.37))

    implicitWidth: 92
    implicitHeight: 168
    opacity: root.revealed ? 0.94 : 0
    transform: Translate {
        id: revealTranslate
        x: root.revealed ? root.revealDistance : MichiSpacing.xs
        Behavior on x {
            enabled: !MichiAccessibility.reducedMotion
            SequentialAnimation {
                PauseAnimation {
                    duration: root.revealed
                        ? Math.round(MichiMotion.micro / 3) : 0
                }
                NumberAnimation {
                    duration: MichiMotion.artwork
                    easing.type: MichiMotion.outCubic
                }
            }
        }
    }

    Behavior on opacity {
        enabled: !MichiAccessibility.reducedMotion
        SequentialAnimation {
            PauseAnimation {
                duration: root.revealed
                    ? Math.round(MichiMotion.micro / 3) : 0
            }
            NumberAnimation {
                duration: root.revealed
                    ? MichiMotion.artwork : MichiMotion.standard
                easing.type: MichiMotion.outCubic
            }
        }
    }

    Image {
        anchors.fill: parent
        source: "../assets/michi-peek.svg"
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        sourceSize.width: Math.round(width * Screen.devicePixelRatio)
        sourceSize.height: Math.round(height * Screen.devicePixelRatio)
    }
}
