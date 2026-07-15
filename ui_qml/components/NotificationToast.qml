import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Controls
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var notification: null
    property int defaultTimeoutMs: 5000
    property bool reducedMotion: false
    property var notificationBridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string objectName: "notificationToast"

    signal dismissed()
    signal actionTriggered()

    objectName: "NotificationToast"

    Accessible.role: Accessible.Notification
    Accessible.name: notification ? (notification.title || notification.text || "") : ""
    Accessible.description: notification ? (notification.message || "") : ""

    width: parent ? parent.width : 0
    height: toastContainer.height + MichiTheme.spacing.lg * 2

    states: [
        State {
            name: "hidden"
            PropertyChanges { target: toastContainer; opacity: 0; y: -toastContainer.height - MichiTheme.spacing.lg }
        },
        State {
            name: "visible"
            PropertyChanges { target: toastContainer; opacity: 1; y: MichiTheme.spacing.lg }
        },
        State {
            name: "dismissing"
            PropertyChanges { target: toastContainer; opacity: 0; y: -toastContainer.height - MichiTheme.spacing.lg * 2 }
        }
    ]

    state: notification ? "visible" : "hidden"

    transitions: [
        Transition {
            from: "hidden"; to: "visible"
            SequentialAnimation {
                PropertyAction { target: toastContainer; property: "visible"; value: true }
                ParallelAnimation {
                    NumberAnimation { target: toastContainer; property: "opacity"; duration: root.reducedMotion ? 1 : MichiTheme.motion.normal; easing.type: Easing.OutCubic }
                    NumberAnimation { target: toastContainer; property: "y"; duration: root.reducedMotion ? 1 : MichiTheme.motion.normal; easing.type: Easing.OutCubic }
                }
            }
        },
        Transition {
            from: "visible"; to: "dismissing"
            ParallelAnimation {
                NumberAnimation { target: toastContainer; property: "opacity"; duration: root.reducedMotion ? 1 : MichiTheme.motion.fast; easing.type: Easing.InCubic }
                NumberAnimation { target: toastContainer; property: "y"; duration: root.reducedMotion ? 1 : MichiTheme.motion.fast; easing.type: Easing.InCubic }
            }
            onRunningChanged: {
                if (!running && root.state === "dismissing") {
                    toastContainer.visible = false
                    root.dismissed()
                }
            }
        },
        Transition {
            from: "dismissing"; to: "hidden"
            PropertyAction { target: toastContainer; property: "visible"; value: false }
        }
    ]

    Rectangle {
        id: toastContainer
        anchors.horizontalCenter: parent.horizontalCenter
        y: MichiTheme.spacing.lg
        width: Math.min(480, parent.width * 0.85)
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfaceCardElevated
        border.width: MichiTheme.borderWidth
        border.color: {
            if (!root.notification) return MichiTheme.colors.borderCard
            switch (root.notification.kind) {
                case "success": return MichiTheme.colors.success
                case "warning": return MichiTheme.colors.warning
                case "error": return MichiTheme.colors.error
                case "progress": return MichiTheme.colors.accentBlue
                default: return MichiTheme.colors.borderCard
            }
        }
        visible: false

        Row {
            id: toastRow
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Rectangle {
                id: typeIndicator
                width: 4
                height: parent.height
                radius: MichiTheme.radiusXs
                color: {
                    if (!root.notification) return "transparent"
                    switch (root.notification.kind) {
                        case "success": return MichiTheme.colors.success
                        case "warning": return MichiTheme.colors.warning
                        case "error": return MichiTheme.colors.error
                        case "progress": return MichiTheme.colors.accentBlue
                        default: return MichiTheme.colors.accentBlue
                    }
                }
            }

            Column {
                id: textColumn
                width: parent.width - typeIndicator.width - dismissBtn.width - (actionBtn.visible ? actionBtn.width + MichiTheme.spacing.sm : 0) - MichiTheme.spacing.md * 2
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    id: titleText
                    width: parent.width
                    text: root.notification ? (root.notification.title || root.notification.text || "") : ""
                    text: root.notificationBridge && root.notificationBridge.currentNotification ? root.notificationBridge.currentNotification.title || "Notificación" : ""
    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var notification: null
    property int defaultTimeoutMs: 5000
    property bool reducedMotion: false

    signal dismissed()
    signal actionTriggered()

    objectName: "NotificationToast"

    Accessible.role: Accessible.Notification
    Accessible.name: notification ? (notification.title || notification.text || "") : ""
    Accessible.description: notification ? (notification.message || "") : ""

    width: parent ? parent.width : 0
    height: toastContainer.height + MichiTheme.spacing.lg * 2

    states: [
        State {
            name: "hidden"
            PropertyChanges { target: toastContainer; opacity: 0; y: -toastContainer.height - MichiTheme.spacing.lg }
        },
        State {
            name: "visible"
            PropertyChanges { target: toastContainer; opacity: 1; y: MichiTheme.spacing.lg }
        },
        State {
            name: "dismissing"
            PropertyChanges { target: toastContainer; opacity: 0; y: -toastContainer.height - MichiTheme.spacing.lg * 2 }
        }
    ]

    state: notification ? "visible" : "hidden"

    transitions: [
        Transition {
            from: "hidden"; to: "visible"
            SequentialAnimation {
                PropertyAction { target: toastContainer; property: "visible"; value: true }
                ParallelAnimation {
                    NumberAnimation { target: toastContainer; property: "opacity"; duration: root.reducedMotion ? 1 : MichiTheme.motion.normal; easing.type: Easing.OutCubic }
                    NumberAnimation { target: toastContainer; property: "y"; duration: root.reducedMotion ? 1 : MichiTheme.motion.normal; easing.type: Easing.OutCubic }
                }
            }
        },
        Transition {
            from: "visible"; to: "dismissing"
            ParallelAnimation {
                NumberAnimation { target: toastContainer; property: "opacity"; duration: root.reducedMotion ? 1 : MichiTheme.motion.fast; easing.type: Easing.InCubic }
                NumberAnimation { target: toastContainer; property: "y"; duration: root.reducedMotion ? 1 : MichiTheme.motion.fast; easing.type: Easing.InCubic }
            }
            onRunningChanged: {
                if (!running && root.state === "dismissing") {
                    toastContainer.visible = false
                    root.dismissed()
                }
            }
        },
        Transition {
            from: "dismissing"; to: "hidden"
            PropertyAction { target: toastContainer; property: "visible"; value: false }
        }
    ]

    Rectangle {
        id: toastContainer
        anchors.horizontalCenter: parent.horizontalCenter
        y: MichiTheme.spacing.lg
        width: Math.min(480, parent.width * 0.85)
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfaceCardElevated
        border.width: MichiTheme.borderWidth
        border.color: {
            if (!root.notification) return MichiTheme.colors.borderCard
            switch (root.notification.kind) {
                case "success": return MichiTheme.colors.success
                case "warning": return MichiTheme.colors.warning
                case "error": return MichiTheme.colors.error
                case "progress": return MichiTheme.colors.accentBlue
                default: return MichiTheme.colors.borderCard
            }
        }
        visible: false

        Row {
            id: toastRow
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Rectangle {
                id: typeIndicator
                width: 4
                height: parent.height
                radius: MichiTheme.radiusXs
                color: {
                    if (!root.notification) return "transparent"
                    switch (root.notification.kind) {
                        case "success": return MichiTheme.colors.success
                        case "warning": return MichiTheme.colors.warning
                        case "error": return MichiTheme.colors.error
                        case "progress": return MichiTheme.colors.accentBlue
                        default: return MichiTheme.colors.accentBlue
                    }
                }
            }

            Column {
                id: textColumn
                width: parent.width - typeIndicator.width - dismissBtn.width - (actionBtn.visible ? actionBtn.width + MichiTheme.spacing.sm : 0) - MichiTheme.spacing.md * 2
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    id: titleText
                    width: parent.width
                    text: root.notification ? (root.notification.title || root.notification.text || "") : ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width - closeBtn.width - MichiTheme.spacing.sm
                    visible: text !== ""
                }

                Text {
                    id: messageText
                    width: parent.width
                    text: root.notification ? (root.notification.message || (root.notification.title ? root.notification.text : "")) : ""
                    color: MichiTheme.colors.textSecondary
                    id: closeBtn
                    text: "✕"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    wrapMode: Text.WordWrap
                    visible: text !== ""
                }
            }

            MichiButton {
                id: actionBtn
                anchors.verticalCenter: parent.verticalCenter
                text: root.notification && root.notification.actionText ? root.notification.actionText : ""
                variant: "ghost"
                visible: root.notification && root.notification.action && root.notification.action !== ""
                onClicked: {
                    if (root.bridge && root.notification) {
                        root.bridge.executeNotificationAction(root.notification.id || "")
                    }
                    root.actionTriggered()
                }

                Accessible.role: Accessible.Button
                Accessible.name: text
            }

            QQC2.AbstractButton {
                id: dismissBtn
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 28
                implicitHeight: 28
                focusPolicy: Qt.StrongFocus

                Accessible.role: Accessible.Button
                Accessible.name: "Descartar notificación"
                Accessible.description: "Cerrar esta notificación"

                contentItem: Text {
                    text: "\u00D7"
                    color: root.activeFocus ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    radius: MichiTheme.radiusSm
                    color: dismissBtn.hovered ? MichiTheme.colors.surfaceHover : "transparent"
                    border.width: dismissBtn.activeFocus ? MichiTheme.focusWidth : 0
                    border.color: MichiTheme.colors.borderFocus
                }

                onClicked: root.dismissToast()

                Keys.onEscapePressed: root.dismissToast()
            }
        }

        MichiProgressBar {
            id: progressBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: root.notification && root.notification.kind === "progress" ? 3 : 0
            value: root.notification ? (root.notification.progress || 0) : 0
            indeterminate: root.notification && root.notification.kind === "progress" && (!root.notification.progress || root.notification.progress < 0)
            visible: root.notification && root.notification.kind === "progress"
            reducedMotion: root.reducedMotion
        }
    }

    Timer {
        id: autoDismissTimer
        interval: {
            if (!root.notification) return 0
            if (root.notification.persistent || root.notification.kind === "error") return 0
            if (root.notification.kind === "progress") return 0
            return root.notification._timeoutMs || root.defaultTimeoutMs
        }
        running: root.notification !== null && !root.notification.persistent && root.notification.kind !== "error" && root.notification.kind !== "progress"
        repeat: false
        onTriggered: root.dismissToast()
    }
                    id: messageText
                    width: parent.width
                    text: root.notification ? (root.notification.message || (root.notification.title ? root.notification.text : "")) : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    wrapMode: Text.WordWrap
                    visible: text !== ""
                }
            }

            MichiButton {
                id: actionBtn
                anchors.verticalCenter: parent.verticalCenter
                text: root.notification && root.notification.actionText ? root.notification.actionText : ""
                variant: "ghost"
                visible: root.notification && root.notification.action && root.notification.action !== ""
                onClicked: {
                    if (root.bridge && root.notification) {
                        root.bridge.executeNotificationAction(root.notification.id || "")
                    }
                    root.actionTriggered()
                }

                Accessible.role: Accessible.Button
                Accessible.name: text
            }

            QQC2.AbstractButton {
                id: dismissBtn
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 28
                implicitHeight: 28
                focusPolicy: Qt.StrongFocus

                Accessible.role: Accessible.Button
                Accessible.name: "Descartar notificación"
                Accessible.description: "Cerrar esta notificación"

                contentItem: Text {
                    text: "\u00D7"
                    color: root.activeFocus ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    radius: MichiTheme.radiusSm
                    color: dismissBtn.hovered ? MichiTheme.colors.surfaceHover : "transparent"
                    border.width: dismissBtn.activeFocus ? MichiTheme.focusWidth : 0
                    border.color: MichiTheme.colors.borderFocus
                }

                onClicked: root.dismissToast()

                Keys.onEscapePressed: root.dismissToast()
            }
        }

        MichiProgressBar {
            id: progressBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: root.notification && root.notification.kind === "progress" ? 3 : 0
            value: root.notification ? (root.notification.progress || 0) : 0
            indeterminate: root.notification && root.notification.kind === "progress" && (!root.notification.progress || root.notification.progress < 0)
            visible: root.notification && root.notification.kind === "progress"
            reducedMotion: root.reducedMotion
        }
    }

    Timer {
        id: autoDismissTimer
        interval: {
            if (!root.notification) return 0
            if (root.notification.persistent || root.notification.kind === "error") return 0
            if (root.notification.kind === "progress") return 0
            return root.notification._timeoutMs || root.defaultTimeoutMs
        }
        running: root.notification !== null && !root.notification.persistent && root.notification.kind !== "error" && root.notification.kind !== "progress"
        repeat: false
        onTriggered: root.dismissToast()
    }

    function dismissToast() {
        if (root.state === "hidden" || root.state === "dismissing") return
        root.state = "dismissing"
        if (root.bridge) root.bridge.dismiss()
    }

    function show(notif) {
        root.notification = notif
        root.state = "visible"
    }

    function hide() {
        root.notification = null
        root.state = "hidden"
    }

    Keys.onEscapePressed: root.dismissToast()
}
