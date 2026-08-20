import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

TextField {
    id: root
    property string accessibleName: ""
    implicitHeight: MichiMetrics.controlMedium
    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.md
    color: enabled ? MichiPalette.textPrimary : MichiPalette.textDisabled
    placeholderTextColor: MichiPalette.textMuted
    selectionColor: MichiPalette.auroraBlue
    selectedTextColor: MichiPalette.obsidian
    font.family: MichiTypography.family
    font.pixelSize: MichiTypography.secondary
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.EditableText
    Accessible.name: accessibleName.length > 0 ? accessibleName : placeholderText

    background: Rectangle {
        id: fieldSurface
        radius: MichiRadius.md
        color: root.enabled ? MichiSemanticColors.controlSurface : MichiPalette.graphite
        border.color: root.activeFocus ? MichiPalette.auroraBlue
            : root.hovered ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
        border.width: root.activeFocus ? 2 : 1
        Behavior on border.color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
        Rectangle {
            visible: root.activeFocus
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: parent.radius
            anchors.rightMargin: parent.radius
            height: 1
            color: MichiPalette.auroraCyan
            opacity: 0.65
        }
    }
}
