import QtQuick
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Progress Bar"
    objectName: "michiProgressBar"
    focus: true
    id: root

    property real value: 0
    property real from: 0
    property real to: 100
    property bool indeterminate: false
    property bool reducedMotion: false
    property string accessibleName: "Progreso"
    property string accessibleDescription: ""

    implicitHeight: 4
    radius: MichiTheme.radiusPill
    color: MichiTheme.colors.controlTrack

    Accessible.role: Accessible.ProgressBar
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    Rectangle {
        width: root.indeterminate ? parent.width * 0.3 : Math.max(0, Math.min(parent.width,
            (root.value - root.from) / Math.max(1, root.to - root.from) * parent.width))
        height: parent.height
        radius: MichiTheme.radiusPill
        color: MichiTheme.colors.accentBlue

        SequentialAnimation on x {
            running: root.indeterminate && !root.reducedMotion
            loops: Animation.Infinite
            PropertyAnimation { target: root; property: "x"; from: -parent.width * 0.3; to: parent.width; duration: 1200 }
            PropertyAnimation { target: root; property: "x"; from: parent.width; to: -parent.width * 0.3; duration: 0 }
        }
    }
}
