import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Switch {
    id: root
    spacing: MichiSpacing.sm
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.CheckBox
    indicator: Rectangle {
        implicitWidth: 36; implicitHeight: 20
        x: root.leftPadding; y: parent.height / 2 - height / 2
        radius: height / 2
        color: root.checked ? MichiPalette.auroraBlue : MichiPalette.smokeRaised
        border.width: 1
        border.color: root.checked ? MichiPalette.auroraBlue : MichiSemanticColors.borderStrong
        Rectangle {
            width: 14; height: 14; radius: 7
            x: root.checked ? parent.width - width - 3 : 3
            anchors.verticalCenter: parent.verticalCenter
            color: root.checked ? MichiPalette.obsidian : MichiPalette.textSecondary
            Behavior on x { NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic } }
        }
        MichiFocusRing { visualFocus: root.visualFocus }
    }
    contentItem: MichiText {
        text: root.text
        role: "secondary"
        leftPadding: root.indicator.width + root.spacing
        verticalAlignment: Text.AlignVCenter
    }
}
