import QtQuick
import "../theme"

Rectangle {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property real value: 0
    property real from: 0
    property real to: 100
    property bool indeterminate: false
    property string variant: "normal"
    property bool reducedMotion: false
    property string accessibleName: "Progreso: " + Math.round((root.value - root.from) / Math.max(1, root.to - root.from) * 100) + "%"
    property string accessibleDescription: ""

    implicitHeight: 4
    radius: MichiTheme.radius.pill
    color: MichiTheme.colors.controlTrack

    Accessible.role: Accessible.ProgressBar
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    Rectangle {
        id: fill
        width: root.indeterminate ? parent.width * 0.3 : Math.max(0, Math.min(parent.width,
            (root.value - root.from) / Math.max(1, root.to - root.from) * parent.width))
        height: parent.height
        radius: MichiTheme.radius.pill
        color: {
            switch (root.variant) {
                case "success": return MichiTheme.colors.success
                case "warning": return MichiTheme.colors.warning
                case "error": return MichiTheme.colors.error
                default: return MichiTheme.colors.accentBlue
            }
        }

        SequentialAnimation on x {
            running: root.indeterminate && !root.reducedMotion
            loops: Animation.Infinite
            PropertyAnimation {
                target: fill
                property: "x"
                from: -parent.width * 0.3
                to: parent.width
                duration: 1200
            }
            PropertyAnimation {
                target: fill
                property: "x"
                from: parent.width
                to: -parent.width * 0.3
                duration: 0
            }
        }
    }
}
