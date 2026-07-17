import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Route Transition"
    objectName: "routeTransition"
    focus: true
    id: root

    property var target: null
    property bool reducedMotion: typeof themeBridge !== "undefined" && themeBridge ? themeBridge.reducedMotion : false

    signal navigate(string route)

    onTargetChanged: {
        if (target) {
            target.opacity = 1.0
            if (!root.reducedMotion) {
                var anim = Qt.createQmlObject(
                    'import QtQuick; NumberAnimation { from: 0; to: 1; duration: 200; easing.type: Easing.OutCubic }',
                    target, "routeAnim")
                anim.start()
            }
        }
    }
}
