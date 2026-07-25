import QtQuick
import "../theme"
import "../components"

Item {
    id: root
    objectName: "pageStackContainer"

    property alias source: routeLoader.source
    property alias asynchronous: routeLoader.asynchronous
    readonly property alias status: routeLoader.status
    readonly property alias item: routeLoader.item

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
    }

    PageSurface {
        anchors.fill: parent
        anchors.leftMargin: root.width < MichiTheme.breakpoints.compact ? 0 : MichiTheme.spacing.sm
        anchors.rightMargin: root.width < MichiTheme.breakpoints.compact ? 0 : MichiTheme.spacing.sm
        anchors.topMargin: MichiTheme.spacing.sm
        anchors.bottomMargin: MichiTheme.spacing.sm

        Loader {
            id: routeLoader
            anchors.fill: parent
            asynchronous: true
            source: ""
            opacity: status === Loader.Ready ? 1.0 : 0.0

            Behavior on opacity {
                NumberAnimation {
                    duration: MichiTheme.motion.fast
                    easing.type: Easing.OutQuart
                }
            }
        }
    }
}
