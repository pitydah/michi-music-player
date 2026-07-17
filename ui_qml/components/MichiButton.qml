import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

QQC2.Button {
    id: root

    property string controlObjectName: ""
    objectName: root.controlObjectName

    property string variant: "primary"
    property string iconText: ""
    property string iconSource: ""
    property string tooltipText: ""
    property bool loading: false
    property string accessibleName: text
    property string accessibleDescription: tooltipText

    topPadding: MichiTheme.spacing.sm
    bottomPadding: MichiTheme.spacing.sm
    leftPadding: MichiTheme.spacing.lg
    rightPadding: MichiTheme.spacing.lg
    spacing: MichiTheme.spacing.sm

    implicitWidth: Math.max(72, contentRow.implicitWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(MichiTheme.minimumInteractiveSize,
                             contentRow.implicitHeight + topPadding + bottomPadding)
    focusPolicy: Qt.StrongFocus
    activeFocusOnTab: enabled && !loading
    enabled: !root.loading

    Accessible.role: Accessible.Button
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    font.pixelSize: MichiTheme.typography.buttonSize
    font.weight: root.variant === "primary" || root.variant === "danger" || root.variant === "success"
                 ? MichiTheme.typography.weightSemiBold
                 : MichiTheme.typography.weightMedium

    background: Rectangle {
        radius: MichiTheme.radius.md
        color: {
            if (!root.enabled || root.loading) return MichiTheme.colors.surfaceDisabled
            if (root.down) return MichiTheme.colors.surfacePressed
            if (root.hovered) return MichiTheme.colors.surfaceHover
            if (root.variant === "primary") return MichiTheme.colors.accentBlue
            if (root.variant === "danger") return MichiTheme.colors.error
            if (root.variant === "success") return MichiTheme.colors.success
            if (root.variant === "ghost") return "transparent"
            return MichiTheme.colors.surfaceCard
        }
        border.width: root.activeFocus ? MichiTheme.focusWidth : (root.variant === "ghost" ? 0 : MichiTheme.borderWidth)
        border.color: {
            if (!root.enabled || root.loading) return "transparent"
            if (root.activeFocus) return MichiTheme.colors.borderFocus
            if (root.variant === "secondary") return MichiTheme.colors.borderCard
            return "transparent"
        }
    }

    contentItem: Item {
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: root.spacing
            opacity: root.loading ? 0 : 1

            Image {
                width: MichiTheme.typography.cardTitleSize
                height: width
                source: root.iconSource
                visible: root.iconSource !== ""
                fillMode: Image.PreserveAspectFit
            }

            Text {
                text: root.iconText
                font.pixelSize: MichiTheme.typography.cardTitleSize
                color: {
                    if (!root.enabled) return MichiTheme.colors.textMuted
                    if (root.variant === "primary" || root.variant === "danger" || root.variant === "success")
                        return MichiTheme.colors.textOnAccent
                    return MichiTheme.colors.textPrimary
                }
                visible: root.iconSource === "" && root.iconText !== ""
            }

            Text {
                text: root.text
                font: root.font
                color: {
                    if (!root.enabled) return MichiTheme.colors.textMuted
                    if (root.variant === "primary" || root.variant === "danger" || root.variant === "success")
                        return MichiTheme.colors.textOnAccent
                    return MichiTheme.colors.textPrimary
                }
                visible: root.text !== ""
            }
        }

        QQC2.BusyIndicator {
            anchors.centerIn: parent
            width: MichiTheme.typography.cardTitleSize
            height: width
            running: root.loading
            visible: root.loading
        }
    }

    QQC2.ToolTip {
        visible: root.hovered && root.tooltipText !== ""
        text: root.tooltipText
        delay: 600
    }
}
