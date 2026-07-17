import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Notification Progress Item"
    objectName: "notificationProgressItem"
    focus: true
    id: root

    property var notification: null
    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool reducedMotion: false

    signal dismissed()
    signal canceled()
    signal actionTriggered(string actionId)


    Accessible.description: {
        if (!root.notification) return ""
        const pct = root.notification.progress !== undefined && root.notification.progress >= 0 ? Math.round(root.notification.progress) + "%" : "indeterminado"
        return (root.notification.message || "") + " " + pct
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
                id: progressIcon
                anchors.verticalCenter: parent.verticalCenter
                width: 8
                height: 8
                radius: MichiTheme.radius.sm
                color: MichiTheme.colors.accentBlue
            }

            Column {
                width: parent.width - progressIcon.width - dismissBtn.width - MichiTheme.spacing.md
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Row {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: root.notification ? (root.notification.title || root.notification.text || "Progreso") : "Progreso"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                        width: parent.width - elapsedText.width - pctText.width - MichiTheme.spacing.sm * 2
                    }

                    Text {
                        id: pctText
                        text: {
                            if (!root.notification) return ""
                            if (root.notification.progress !== undefined && root.notification.progress >= 0) return Math.round(root.notification.progress) + "%"
                            return "--%"
                        }
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        id: elapsedText
                        text: {
                            if (!root.notification || !root.notification.timestamp) return ""
                            const elapsed = Math.round((Date.now() / 1000) - root.notification.timestamp)
                            if (elapsed < 60) return elapsed + "s"
                            if (elapsed < 3600) return Math.floor(elapsed / 60) + "m " + (elapsed % 60) + "s"
                            return Math.floor(elapsed / 3600) + "h " + Math.floor((elapsed % 3600) / 60) + "m"
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
                iconSource: "qrc:/icons/nav_back.svg"
                tooltipText: "Eliminar"
                accessibleName: "Eliminar este elemento de progreso"
                onClicked: root.dismissItem()
                transform: Rotation { angle: 45 }
            }
        }

        MichiProgressBar {
            Accessible.role: Accessible.ProgressBar

            id: progressBar
            activeFocusOnTab: true

            width: parent.width
            value: root.notification && root.notification.progress !== undefined && root.notification.progress >= 0 ? root.notification.progress : 0
            from: 0
            to: 100
            indeterminate: root.notification && (root.notification.progress === undefined || root.notification.progress < 0)
            reducedMotion: root.reducedMotion
            accessibleName: root.notification ? (root.notification.title || "Progreso") : "Progreso"
            accessibleDescription: pctText.text
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Restante: " + estimatedRemaining()
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.notification && root.notification.progress !== undefined && root.notification.progress > 0 && root.notification.progress < 100
            }

            Item { width: 1; height: 1 }
                Accessible.role: Accessible.Button

                activeFocusOnTab: true


            MichiButton {
                id: cancelBtn
                text: "Cancelar"
                variant: "ghost"
                implicitHeight: 28
                visible: root.notification && root.notification.job_id
                onClicked: {
                    if (root.bridge && root.notification && root.notification.job_id) {
                        root.bridge.cancelJobById(root.notification.job_id)
                    }
                    root.canceled()
                    root.actionTriggered("cancelJob")
                }

                Accessible.description: "Detener este proceso"
            }
        }
    }

    Timer {
        id: elapsedTimer
        interval: 1000
        running: root.notification !== null && root.notification.kind === "progress"
        repeat: true
        onTriggered: {
            if (!root.notification || !root.notification.timestamp) {
                elapsedText.text = ""
                return
            }
            var elapsed = Math.round((Date.now() / 1000) - root.notification.timestamp)
            if (elapsed < 60)
                elapsedText.text = elapsed + "s"
            else if (elapsed < 3600)
                elapsedText.text = Math.floor(elapsed / 60) + "m " + (elapsed % 60) + "s"
            else
                elapsedText.text = Math.floor(elapsed / 3600) + "h " + Math.floor((elapsed % 3600) / 60) + "m"
        }
    }

    NumberAnimation {
        id: removeAnim
        target: root
        property: "opacity"
        from: 1
        to: 0
        duration: root.reducedMotion ? 1 : MichiTheme.motion.normal
        onFinished: root.dismissed()
    }

    function estimatedRemaining() {
        if (!root.notification || !root.notification.timestamp || !root.notification.progress || root.notification.progress <= 0) return "--"
        const elapsed = Math.round((Date.now() / 1000) - root.notification.timestamp)
        if (elapsed <= 0) return "--"
        const remaining = Math.round((elapsed / root.notification.progress) * (100 - root.notification.progress))
        if (remaining < 60) return remaining + "s"
        if (remaining < 3600) return Math.floor(remaining / 60) + "m " + (remaining % 60) + "s"
        return Math.floor(remaining / 3600) + "h " + Math.floor((remaining % 3600) / 60) + "m"
    }

    function dismissItem() {
        if (root.bridge && root.notification) {
            root.bridge.dismiss()
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
