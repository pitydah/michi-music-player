import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Button {
    id: root
    property string variant: "primary"
    property string iconName: ""
    property bool selected: checked
    readonly property bool primary: variant === "primary"
    readonly property bool ghost: variant === "ghost"

    implicitHeight: MichiMetrics.controlMedium
    implicitWidth: Math.max(72, contentRow.implicitWidth + MichiSpacing.xl * 2)
    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.md
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.role: Accessible.Button
    Accessible.name: text

    contentItem: Row {
        id: contentRow
        spacing: MichiSpacing.sm
        anchors.centerIn: parent
        MichiIcon {
            visible: root.iconName !== ""
            name: root.iconName
            width: MichiMetrics.iconSmall
            height: width
            iconColor: label.color
            anchors.verticalCenter: parent.verticalCenter
        }
        MichiText {
            id: label
            text: root.text
            role: "secondary"
            color: !root.enabled ? MichiPalette.textDisabled
                : root.primary ? MichiPalette.obsidian
                : root.selected || root.hovered ? MichiPalette.textPrimary
                : MichiPalette.textSecondary
            font.weight: root.primary || root.selected ? Font.DemiBold : Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    background: Rectangle {
        id: buttonSurface
        radius: MichiRadius.md
        color: !root.enabled ? MichiPalette.graphite
            : root.primary ? (root.pressed ? MichiSemanticColors.auroraPressed
                : root.hovered ? MichiSemanticColors.auroraHover : MichiPalette.auroraBlue)
            : root.pressed ? MichiSemanticColors.surfacePressed
            : root.hovered ? MichiSemanticColors.surfaceHover
            : root.selected ? MichiSemanticColors.surfaceSelected
            : root.ghost ? "transparent" : MichiPalette.smoke
        border.width: root.primary ? 0 : 1
        border.color: root.selected ? MichiPalette.auroraBlue : MichiSemanticColors.borderSubtle
        y: root.pressed ? 1 : 0
        Behavior on color { ColorAnimation { duration: MichiMotion.micro } }
        Behavior on y { NumberAnimation { duration: MichiMotion.instant } }
        MichiFocusRing { visualFocus: root.visualFocus }
    }
}
