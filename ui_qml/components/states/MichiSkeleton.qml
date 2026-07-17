import QtQuick
import "../../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Skeleton"
    objectName: "michiSkeleton"
    focus: true
    id: root

    property string title: "Cargando"
    property string message: ""
    property string iconName: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property bool busy: true
    property string details: ""
    property bool reducedMotion: false

    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitWidth: 180
    implicitHeight: MichiTheme.rowHeightComfortable
    radius: MichiTheme.radius.sm
    color: MichiTheme.colors.skeletonBase

    Accessible.description: message

    SequentialAnimation on opacity {
        running: root.busy && !root.reducedMotion
        loops: Animation.Infinite
        NumberAnimation { from: 0.55; to: 1.0; duration: MichiTheme.motion.durationSlow }
        NumberAnimation { from: 1.0; to: 0.55; duration: MichiTheme.motion.durationSlow }
    }
}
