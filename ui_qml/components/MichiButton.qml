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
    property bool symbolic: true
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
    font.weight: root.variant === "primary" || root.variant === "danger" || root.variant === "success" || root.variant === "accent"
                 ? MichiTheme.typography.weightSemiBold
                 : MichiTheme.typography.weightMedium

    background: Rectangle {
        radius: MichiTheme.radius.md
        color: {
            if (!root.enabled || root.loading) return MichiTheme.colors.surfaceDisabled
            if (root.variant === "primary" || root.variant === "accent") {
                if (root.down) return Qt.darker(MichiTheme.colors.accentPrimary, 1.18)
                if (root.hovered) return Qt.lighter(MichiTheme.colors.accentPrimary, 1.08)
                return MichiTheme.colors.accentPrimary
            }
            if (root.variant === "danger") {
                if (root.down) return Qt.darker(MichiTheme.colors.error, 1.16)
                if (root.hovered) return Qt.lighter(MichiTheme.colors.error, 1.06)
                return MichiTheme.colors.error
            }
            if (root.variant === "success") {
                if (root.down) return Qt.darker(MichiTheme.colors.success, 1.16)
                if (root.hovered) return Qt.lighter(MichiTheme.colors.success, 1.06)
                return MichiTheme.colors.success
            }
            if (root.down) return MichiTheme.colors.surfacePressed
            if (root.hovered) return MichiTheme.colors.surfaceCardHover
            if (root.variant === "ghost") return "transparent"
            if (root.variant === "tonal") return MichiTheme.colors.accentSurface
            return MichiTheme.colors.surfaceGlass
        }
        border.width: root.activeFocus ? MichiTheme.focusWidth : (root.variant === "ghost" ? 0 : MichiTheme.borderWidth)
        border.color: {
            if (!root.enabled || root.loading) return "transparent"
            if (root.activeFocus) return MichiTheme.colors.borderFocus
            if (root.variant === "secondary" || root.variant === "outline") return root.hovered
                    ? MichiTheme.colors.borderHover : MichiTheme.colors.borderCard
            if (root.variant === "tonal") return MichiTheme.colors.accentSeparator
            return "transparent"
        }
        scale: root.down ? 0.985 : 1.0
        Behavior on color {
            ColorAnimation {
                duration: MichiTheme.motion.fast
                easing.type: MichiTheme.motion.easing.standard
            }
        }
        Behavior on scale {
            NumberAnimation {
                duration: MichiTheme.motion.fast
                easing.type: MichiTheme.motion.easing.emphasis
            }
        }
    }

    contentItem: Item {
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: root.spacing
            visible: !root.loading

            Image {
                width: MichiTheme.iconSizeRegular
                height: width
                source: root.iconSource
                visible: root.iconSource !== "" && !root.symbolic
                fillMode: Image.PreserveAspectFit
            }

            MichiIcon {
                width: MichiTheme.iconSizeRegular
                height: width
                source: root.iconSource
                size: MichiTheme.iconSizeRegular
                color: root.variant === "primary" || root.variant === "accent"
                       || root.variant === "danger" || root.variant === "success"
                       ? MichiTheme.colors.textOnAccent : MichiTheme.colors.textPrimary
                visible: root.iconSource !== "" && root.symbolic
                accessibleName: ""
            }

            Text {
                text: root.iconText
                font.pixelSize: MichiTheme.typography.cardTitleSize
                color: {
                    if (!root.enabled) return MichiTheme.colors.textMuted
                    if (root.variant === "primary" || root.variant === "accent"
                            || root.variant === "danger" || root.variant === "success")
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
                    if (root.variant === "primary" || root.variant === "accent"
                            || root.variant === "danger" || root.variant === "success")
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
