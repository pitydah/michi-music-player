import QtQuick
import "../theme"

Item {
    id: root

    property Item target

    OpacityAnimator {
        target: root.target
        from: 0.0
        to: 1.0
        duration: MichiTheme.motion.fast
        easing.type: MichiTheme.motion.easing.standard
    }
}
