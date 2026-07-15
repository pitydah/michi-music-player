import QtQuick
import "../theme"

Item {
    id: root

    property Item target
    property int duration: MichiTheme.motion.fast

    objectName: "routeTransition"
    Accessible.role: Accessible.Pane
    Accessible.name: "Transición de ruta"

    onTargetChanged: {
        if (target) {
            target.opacity = 0.0
            var anim = Qt.createQmlObject(
                "import QtQuick; NumberAnimation { to: 1.0; duration: " + duration + "; easing.type: Easing.OutCubic }",
                root, "routeFade")
            anim.target = target
            anim.property = "opacity"
            anim.start()
        }
    }
}
