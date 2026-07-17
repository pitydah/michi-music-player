import QtQuick
import QtQuick.Animators
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Route Transition"
    objectName: "routeTransition"
    focus: true
    id: root

    property Item target
    property int duration: MichiTheme.motion.fast
    property bool reducedMotion: false

    onTargetChanged: {
        if (target) {
            target.opacity = 1.0
            if (!root.reducedMotion) {
                var anim = OpacityAnimator.createObject(target, {
                    "from": 0,
                    "to": 1,
                    "duration": root.reducedMotion ? 0 : 200,
                    "easing.type": Easing.OutCubic
                })
                anim.start()
            }
        }
    }
}
