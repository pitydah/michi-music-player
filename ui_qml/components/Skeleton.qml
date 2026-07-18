import QtQuick
import "../theme"

Rectangle {
    id: root

    property int skeletonWidth: 200
    property int skeletonHeight: 16
    property int skeletonRadius: MichiTheme.radius.sm

    width: skeletonWidth
    height: skeletonHeight
    radius: skeletonRadius
    color: MichiTheme.colors.surfaceSubtle

    SequentialAnimation on opacity {
        loops: Animation.Infinite
        PropertyAnimation { to: 0.3; duration: 800; easing.type: Easing.InOutQuad }
        PropertyAnimation { to: 0.8; duration: 800; easing.type: Easing.InOutQuad }
    }
}
