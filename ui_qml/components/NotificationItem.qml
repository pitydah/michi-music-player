import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root
    objectName: "notificationItem"
    focus: true

    property var notification: null
    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool reducedMotion: false

    signal dismissed()
    signal actionTriggered(string actionId)

    Accessible.role: Accessible.Pane
    Accessible.name: notification ? (notification.title || notification.text || "Notificación") : "Notificación"
    Accessible.description: {
        if (!notification)
            return ""
        var parts = []
        if (notification.message)
            parts.push(notification.message)
        if (notification.kind)
            parts.push("Tipo: " + notification.kind)
        if (notification.progress !== undefined && notification.progress >= 0)
            parts.push(Math.round(notification.progress) + "%")
        return parts.join(". ")
    }

    implicitHeight: contentColumn.implicitHeight + MichiTheme.spacing.md * 2
    radius: MichiTheme.radius.md
    color: activeFocus ? MichiTheme.colors.surfaceHover : MichiTheme.colors.surfaceCard
    border.width: activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
    border.color: activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

    Behavior on color {
        ColorAnimation { duration: root.reducedMotion ? 1 : MichiTheme.motion.fast }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.sm

            Rectangle {
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 6
                width: 8
                height: 8
                radius: 4
                color: {
                    if (!root.notification)
                        return MichiTheme.colors.accentBlue
                    switch (root.notification.kind) {
                    case "success": return MichiTheme.colors.success
                    case "warning": return MichiTheme.colors.warning
                    case "error": return MichiTheme.colors.error
                    case "progress": return MichiTheme.colors.accentBlue
                    default: return MichiTheme.colors.accentBlue
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.sm

                    Text {
                        Layout.fillWidth: true
                        text: root.notification
                            ? (root.notification.title || root.notification.text || "")
                            : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                    }

                    Text {
                        text: root.relativeTime()
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: root.notification ? (root.notification.message || "") : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                    visible: text !== ""
                }
            }

            MichiIconButton {
                Layout.alignment: Qt.AlignTop
                btnSize: 24
                iconSource: "../../icons/nav_back.svg"
                tooltipText: "Eliminar"
                accessibleName: "Eliminar esta notificación"
                transform: Rotation { angle: 45 }
                onClicked: root.dismissItem()
            }
        }

        QQC2.ProgressBar {
            Layout.fillWidth: true
            visible: root.notification
                && root.notification.progress !== undefined
                && root.notification.progress >= 0
            from: 0
            to: 100
            value: root.notification && root.notification.progress !== undefined
                ? Number(root.notification.progress)
                : 0
            indeterminate: root.notification && Number(root.notification.progress) < 0
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.sm
            visible: root.notification
                && (root.notification.action || root.notification.job_id)

            Item { Layout.fillWidth: true }

            MichiButton {
                text: root.actionLabel()
                variant: root.notification && root.notification.kind === "error" ? "danger" : "ghost"
                visible: root.notification && Boolean(root.notification.action)
                onClicked: root.activatePrimaryAction()
            }

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                visible: root.notification
                    && root.notification.kind === "progress"
                    && Boolean(root.notification.job_id)
                onClicked: {
                    if (root.bridge && root.notification)
                        root.bridge.cancelJobById(String(root.notification.job_id))
                    root.actionTriggered("cancelJob")
                }
            }
        }
    }

    NumberAnimation {
        id: removeAnimation
        target: root
        property: "opacity"
        from: 1
        to: 0
        duration: root.reducedMotion ? 1 : MichiTheme.motion.normal
        onFinished: root.dismissed()
    }

    function notificationId() {
        return root.notification && root.notification.id !== undefined
            ? String(root.notification.id)
            : ""
    }

    function dismissItem() {
        if (root.bridge && root.notification)
            root.bridge.dismiss(root.notificationId())
        removeAnimation.start()
    }

    function actionLabel() {
        if (!root.notification)
            return ""
        if (root.notification.actionText)
            return root.notification.actionText
        if (root.notification.action === "cancelJob")
            return "Cancelar"
        if (root.notification.action === "retry")
            return "Reintentar"
        if (root.notification.action === "openJob")
            return "Ver detalle"
        return root.notification.action ? "Abrir" : ""
    }

    function activatePrimaryAction() {
        if (!root.notification || !root.notification.action || !root.bridge)
            return
        root.bridge.executeNotificationAction(root.notificationId())
        root.actionTriggered(root.notification.action)
    }

    function relativeTime() {
        if (!root.notification || !root.notification.timestamp)
            return ""
        var now = new Date()
        var timestamp = new Date(Number(root.notification.timestamp) * 1000)
        var seconds = Math.max(0, Math.round((now - timestamp) / 1000))
        if (seconds < 60)
            return "ahora"
        if (seconds < 3600)
            return Math.floor(seconds / 60) + "m"
        if (seconds < 86400)
            return Math.floor(seconds / 3600) + "h"
        return Math.floor(seconds / 86400) + "d"
    }

    Keys.onReturnPressed: root.activatePrimaryAction()
    Keys.onEnterPressed: root.activatePrimaryAction()
    Keys.onEscapePressed: root.dismissItem()
}
