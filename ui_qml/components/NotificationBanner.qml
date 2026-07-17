import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Notification Banner"
    objectName: "notificationBanner"
    focus: true
    id: root

    property string kind: "info"
    property string title: ""
    property string message: ""
    property string actionText: ""
    property string actionId: ""
    property bool compact: false
    property bool showDismiss: true
    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null

    signal dismissed()
    signal actionTriggered()


    Accessible.description: root.message !== root.title ? root.message : ""

    implicitHeight: contentRow.implicitHeight + MichiTheme.spacing.md * 2
    radius: MichiTheme.radius.md
    color: {
        switch (root.kind) {
            case "success": return MichiTheme.colors.badgeActiveBg
            case "warning": return MichiTheme.colors.badgeWarningBg
            case "error":   return MichiTheme.colors.badgeDangerBg
            default:        return MichiTheme.colors.badgeInfoBg
        }
    }
    border.width: MichiTheme.borderWidth
    border.color: {
        switch (root.kind) {
            case "success": return MichiTheme.colors.success
            case "warning": return MichiTheme.colors.warning
            case "error":   return MichiTheme.colors.error
            default:        return MichiTheme.colors.accentBlue
        }
    }

    Row {
        id: contentRow
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Rectangle {
            id: iconDot
            anchors.verticalCenter: parent.verticalCenter
            width: 8
            height: 8
            radius: MichiTheme.radius.sm
            color: {
                switch (root.kind) {
                    case "success": return MichiTheme.colors.success
                    case "warning": return MichiTheme.colors.warning
                    case "error":   return MichiTheme.colors.error
                    default:        return MichiTheme.colors.accentBlue
                }
            }
            visible: !root.compact
        }

        Column {
            id: textColumn
            width: parent.width - iconDot.width - (actionBtn.visible ? actionBtn.width + MichiTheme.spacing.sm : 0) - (root.showDismiss ? closeBtn.width + MichiTheme.spacing.sm : 0) - MichiTheme.spacing.md * 2
            anchors.verticalCenter: parent.verticalCenter
            spacing: MichiTheme.spacing.xs

            Text {
                width: parent.width
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: root.compact ? MichiTheme.typography.bodySize : MichiTheme.typography.cardTitleSize
                font.weight: root.title ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                elide: Text.ElideRight
                visible: text !== ""
            }

            Text {
                width: parent.width
                text: root.message
                color: MichiTheme.colors.textSecondary
                font.pixelSize: root.compact ? MichiTheme.typography.captionSize : MichiTheme.typography.bodySize
                elide: Text.ElideRight
                maximumLineCount: root.compact ? 1 : 2
                wrapMode: Text.WordWrap
                visible: text !== "" && !root.compact
            }
        }

        MichiButton {
            id: actionBtn
            objectName: "notificationActionButton"
            anchors.verticalCenter: parent.verticalCenter
            text: root.actionText
            variant: "ghost"
            visible: root.actionText !== "" && root.actionId !== ""
            onClicked: {
                if (root.bridge && root.actionId) {
                    root.bridge.execute(actionId)
                }
                root.actionTriggered()
            }

        }

        MichiIconButton {
            id: closeBtn
            objectName: "notificationCloseButton"
            anchors.verticalCenter: parent.verticalCenter
            btnSize: 24
            iconSource: "qrc:/icons/nav_back.svg"
            tooltipText: "Cerrar"
            accessibleName: "Cerrar este banner"
            visible: root.showDismiss
            onClicked: {
                root.dismissed()
                root.visible = false
            }
            transform: Rotation { angle: 45 }
        }
    }

    Keys.onEscapePressed: {
        root.dismissed()
        root.visible = false
    }
}
