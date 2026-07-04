import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

QQC2.Button {
    id: root

    property string variant: "primary"
    property string iconText: ""

    topPadding: MichiTheme.spacing.sm
    bottomPadding: MichiTheme.spacing.sm
    leftPadding: MichiTheme.spacing.lg
    rightPadding: MichiTheme.spacing.lg
    spacing: MichiTheme.spacing.sm

    implicitWidth: Math.max(72, contentRow.implicitWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(30, contentRow.implicitHeight + topPadding + bottomPadding)

    font.pixelSize: MichiTheme.typography.bodySize
    font.weight: MichiTheme.typography.weightMedium

    background: Rectangle {
        radius: MichiTheme.radiusMd
        color: {
            if (!root.enabled) return Qt.rgba(1,1,1,0.04)
            if (root.down) return Qt.rgba(1,1,1,0.12)
            if (root.hovered) return Qt.rgba(1,1,1,0.08)
            if (root.variant === "primary") return MichiTheme.colors.accentBlue
            if (root.variant === "danger") return MichiTheme.colors.error
            return Qt.rgba(1,1,1,0.06)
        }
        border.width: root.variant === "ghost" ? 0 : MichiTheme.borderWidth
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus : Qt.rgba(1,1,1,0.06)
    }

    contentItem: Item {
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: root.spacing

            Text {
                text: root.iconText
                font.pixelSize: MichiTheme.typography.cardTitleSize
                color: {
                    if (!root.enabled) return Qt.rgba(1,1,1,MichiTheme.opacityDisabled)
                    if (root.variant === "primary") return MichiTheme.colors.textOnAccent
                    return MichiTheme.colors.textPrimary
                }
                visible: root.iconText !== ""
            }
            Text {
                text: root.text
                font: root.font
                color: {
                    if (!root.enabled) return Qt.rgba(1,1,1,MichiTheme.opacityDisabled)
                    if (root.variant === "primary") return MichiTheme.colors.textOnAccent
                    return MichiTheme.colors.textPrimary
                }
                visible: root.text !== ""
            }
        }
    }

    QQC2.ToolTip {
        visible: root.hovered && root.text === ""
        text: root.text
        delay: 600
    }
}
