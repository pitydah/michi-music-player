import QtQuick
import "../theme"

// MichiPeek — brand-specific playlist reveal. It carries no information;
// the card remains fully usable when motion is reduced or imagery is unseen.
Item {
    id: root

    property bool revealed: false
    readonly property real revealDistance: Math.max(28, Math.min(40, width * 0.55))

    implicitWidth: 68
    implicitHeight: 136
    opacity: root.revealed ? 1 : 0
    transform: Translate {
        id: revealTranslate
        x: root.revealed ? root.revealDistance : MichiSpacing.xs
        Behavior on x {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation {
                duration: MichiMotion.artwork
                easing.type: MichiMotion.outCubic
            }
        }
    }

    Behavior on opacity {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation {
            duration: root.revealed ? MichiMotion.artwork : MichiMotion.standard
            easing.type: MichiMotion.outCubic
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
