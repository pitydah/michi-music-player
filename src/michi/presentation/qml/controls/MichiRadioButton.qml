import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

RadioButton {
    id: root
    spacing: MichiSpacing.sm
    focusPolicy: Qt.StrongFocus
    indicator: Rectangle {
        implicitWidth: 18; implicitHeight: 18
        x: root.leftPadding; y: parent.height / 2 - height / 2
        radius: width / 2
        color: "transparent"
        border.width: root.checked ? 2 : 1
        border.color: root.checked ? MichiPalette.auroraBlue : MichiSemanticColors.borderStrong
        Rectangle {
            anchors.centerIn: parent
            width: 8; height: 8; radius: 4
            visible: root.checked
            color: MichiPalette.auroraBlue
        }
        MichiFocusRing { visualFocus: root.visualFocus; ringRadius: width / 2 + 2 }
    }
    contentItem: MichiText {
        text: root.text
        role: "secondary"
        leftPadding: root.indicator.width + root.spacing
        verticalAlignment: Text.AlignVCenter
    }
}
