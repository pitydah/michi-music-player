import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

CheckBox {
    id: root
    spacing: MichiSpacing.sm
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    indicator: Rectangle {
        implicitWidth: 18; implicitHeight: 18
        x: root.leftPadding
        y: parent.height / 2 - height / 2
        radius: MichiRadius.xs
        color: root.checked ? MichiPalette.auroraBlue : "transparent"
        border.width: 1
        border.color: root.checked ? MichiPalette.auroraBlue : MichiSemanticColors.borderStrong
        MichiText {
            anchors.centerIn: parent
            text: "✓"
            visible: root.checked
            color: MichiPalette.obsidian
            font.weight: Font.Bold
        }
        MichiFocusRing { visualFocus: root.visualFocus }
    }
    contentItem: MichiText {
        text: root.text
        role: "secondary"
        leftPadding: root.indicator.width + root.spacing
        color: root.enabled ? MichiPalette.textPrimary : MichiPalette.textDisabled
        verticalAlignment: Text.AlignVCenter
    }
}
