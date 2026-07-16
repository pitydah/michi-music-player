import QtQuick
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
            target.opacity = root.reducedMotion ? 1.0 : 0.0
            if (!root.reducedMotion) {
                var anim = Qt.createQmlObject(
                    "import QtQuick; NumberAnimation { to: 1.0; duration: " + root.duration + "; easing.type: Easing.OutCubic }",
                    root, "routeFade")
                anim.target = target
                anim.property = "opacity"
                anim.start()
            }
        }
    }
}
