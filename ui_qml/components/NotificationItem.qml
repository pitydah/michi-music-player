import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: root.notification
        ? (root.notification.title || root.notification.text || qsTr("Notificación"))
        : qsTr("Notificación")
    objectName: "notificationItem"
    focus: true
    id: root

    property var notification: null
    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool reducedMotion: false

    signal dismissed()
    signal actionTriggered(string actionId)


    Accessible.description: {
        if (!root.notification) return ""
        const parts = []
        if (root.notification.message) parts.push(root.notification.message)
        if (root.notification.kind) parts.push("Tipo: " + root.notification.kind)
        if (root.notification.progress !== undefined && root.notification.progress >= 0) parts.push(Math.round(root.notification.progress) + "%")
        return parts.join(". ")
    }

    implicitHeight: contentColumn.implicitHeight + MichiTheme.spacing.md * 2
    radius: MichiTheme.radius.md
    color: root.activeFocus ? MichiTheme.colors.surfaceHover : MichiTheme.colors.surfaceCard
    border.width: root.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
    border.color: root.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

    Behavior on color {
        ColorAnimation { duration: root.reducedMotion ? 1 : MichiTheme.motion.fast }
    }

    Column {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Rectangle {
                id: typeIcon
                anchors.verticalCenter: parent.verticalCenter
                width: 8
                height: 8
                radius: MichiTheme.radius.sm
                color: {
                    if (!root.notification) return MichiTheme.colors.accentBlue
                    switch (root.notification.kind) {
                        case "success": return MichiTheme.colors.success
                        case "warning": return MichiTheme.colors.warning
                        case "error":   return MichiTheme.colors.error
                        case "progress": return MichiTheme.colors.accentBlue
                        default:        return MichiTheme.colors.accentBlue
                    }
                }
            }

            Column {
                width: parent.width - typeIcon.width - dismissBtn.width - MichiTheme.spacing.md
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Row {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: root.notification ? (root.notification.title || root.notification.text || "") : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                        width: parent.width - timestampText.width - MichiTheme.spacing.sm
                    }

                    Text {
                        id: timestampText
                        text: {
                            if (!root.notification || !root.notification.timestamp) return ""
                            const now = new Date()
                            const ts = new Date(root.notification.timestamp * 1000)
                            const diff = Math.round((now - ts) / 1000)
                            if (diff < 60) return "ahora"
                            if (diff < 3600) return Math.floor(diff / 60) + "m"
                            if (diff < 86400) return Math.floor(diff / 3600) + "h"
                            return Math.floor(diff / 86400) + "d"
                        }
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Text {
                    width: parent.width
                    text: root.notification ? (root.notification.message || "") : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    wrapMode: Text.WordWrap
                    visible: text !== ""
                }
            }

            MichiIconButton {
                id: dismissBtn
                anchors.verticalCenter: parent.verticalCenter
                btnSize: 24
                iconSource: "../../icons/nav_back.svg"
                tooltipText: "Eliminar"
                accessibleName: "Eliminar esta notificación de la lista"
                onClicked: root.dismissItem()
                transform: Rotation { angle: 45 }
            }
        }

        Row {
            id: actionRow
            width: parent.width
            spacing: MichiTheme.spacing.sm
            visible: root.notification && (root.notification.action || root.notification.job_id || root.notification.kind === "progress")

            MichiButton {
                Accessible.role: Accessible.Button

                id: primaryActionBtn
                activeFocusOnTab: true

                text: {
                    if (!root.notification) return ""
                    if (root.notification.actionText) return root.notification.actionText
                    if (root.notification.action === "cancelJob") return "Cancelar"
                    if (root.notification.action === "retry") return "Reintentar"
                    if (root.notification.action === "openJob") return "Ver detalle"
                    if (root.notification.action) return "Abrir"
                    return ""
                }
                variant: root.notification && root.notification.kind === "error" ? "danger" : "ghost"
                visible: root.notification && root.notification.action !== ""
                onClicked: {
                    if (root.bridge && root.notification) {
                        root.bridge.executeNotificationAction(root.notification.id || "")
                    }
                    root.actionTriggered(root.notification ? root.notification.action : "")
                }

            }

            MichiButton {
                id: cancelBtn
                text: qsTr("Cancelar")
                variant: "ghost"
                visible: root.notification && root.notification.kind === "progress" && root.notification.job_id
                onClicked: {
                    if (root.bridge && root.notification && root.notification.job_id) {
                        root.bridge.cancelJobById(root.notification.job_id)
                    }
                    root.actionTriggered("cancelJob")
                }

            }
        }
    }

    NumberAnimation {
        id: removeAnim
        target: root
        property: "opacity"
        from: 1
        to: 0
        duration: root.reducedMotion ? 1 : MichiTheme.motion.durationNormal
        onFinished: root.dismissed()
    }

    function dismissItem() {
        if (root.bridge && root.notification) {
            root.bridge.dismiss(root.notification.id || "")
        }
        removeAnim.start()
    }

    function activatePrimaryAction() {
        if (root.notification && root.notification.action && root.bridge) {
            root.bridge.executeNotificationAction(root.notification.id || "")
            root.actionTriggered(root.notification.action)
        }
    }

    Keys.onReturnPressed: root.activatePrimaryAction()
    Keys.onEnterPressed: root.activatePrimaryAction()
    Keys.onEscapePressed: root.dismissItem()
}
