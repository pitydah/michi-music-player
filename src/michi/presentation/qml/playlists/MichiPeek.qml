import QtQuick
import "../theme"

// MichiPeek — brand-specific playlist reveal. It carries no information;
// the card remains fully usable when motion is reduced or imagery is unseen.
Item {
    id: root

    property bool revealed: false
    // The cover occludes most of the body. Only 32–40 px of profile,
    // eye, whiskers and paw clear its right edge on hover/focus.
    readonly property real revealDistance: Math.max(32, Math.min(40, width * 0.42))

    implicitWidth: 96
    implicitHeight: 176
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
