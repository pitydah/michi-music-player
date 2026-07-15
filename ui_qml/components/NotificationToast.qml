import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property var notificationBridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string objectName: "notificationToast"

    Accessible.role: Accessible.Alert
    Accessible.name: root.notificationBridge && root.notificationBridge.currentNotification ? root.notificationBridge.currentNotification.text : ""

    onVisibleChanged: {
        if (visible) {
            slideAnim.start()
        }
    }

    NumberAnimation on opacity {
        id: fadeAnim
        from: 0
        to: 1
        duration: MichiTheme.motion.normal
        easing.type: Easing.OutCubic
    }

    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 80
        width: Math.min(420, parent.width * 0.85)
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfaceCardElevated
        border.width: MichiTheme.borderWidth
        border.color: borderColorForKind()
        clip: true

        transform: Translate {
            id: slideTransform
            y: 60
        }

        SequentialAnimation {
            id: slideAnim
            PropertyAnimation {
                target: slideTransform; property: "y"; from: 60; to: 0
                duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic
            }
        }

        function borderColorForKind() {
            if (!root.notificationBridge || !root.notificationBridge.currentNotification) return MichiTheme.colors.borderCard
            switch (root.notificationBridge.currentNotification.kind) {
                case "success": return MichiTheme.colors.success
                case "warning": return MichiTheme.colors.warning
                case "error": return MichiTheme.colors.error
                default: return MichiTheme.colors.accentBlue
            }
        }

        function backgroundColorForKind() {
            if (!root.notificationBridge || !root.notificationBridge.currentNotification) return "transparent"
            switch (root.notificationBridge.currentNotification.kind) {
                case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.12)
                case "warning": return Qt.rgba(1.0, 0.75, 0.14, 0.12)
                case "error": return Qt.rgba(1.0, 0.44, 0.44, 0.12)
                default: return Qt.rgba(0.561, 0.718, 1.0, 0.08)
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.xs

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    id: titleText
                    text: root.notificationBridge && root.notificationBridge.currentNotification ? root.notificationBridge.currentNotification.title || "Notificación" : ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width - closeBtn.width - MichiTheme.spacing.sm
                    visible: text !== ""
                }

                Text {
                    id: closeBtn
                    text: "✕"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { if (root.notificationBridge) root.notificationBridge.dismiss() }
                    }

                    Accessible.role: Accessible.Button
                    Accessible.name: "Descartar notificación"
                }
            }

            Text {
                text: root.notificationBridge && root.notificationBridge.currentNotification ? root.notificationBridge.currentNotification.text : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
                visible: text !== ""
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.notificationBridge && root.notificationBridge.currentNotification && root.notificationBridge.currentNotification.action && root.notificationBridge.currentNotification.action !== ""

                MichiButton {
                    text: "Ver"
                    variant: "primary"
                    onClicked: { if (root.notificationBridge) root.notificationBridge.executeCurrentAction() }
                }
            }

            MichiProgressBar {
                width: parent.width
                value: root.notificationBridge && root.notificationBridge.currentNotification ? root.notificationBridge.currentNotification.progress || 0 : 0
                visible: root.notificationBridge && root.notificationBridge.currentNotification && root.notificationBridge.currentNotification.progress >= 0
            }
        }

        Timer {
            id: dismissTimer
            interval: 5000
            running: root.visible && root.notificationBridge && root.notificationBridge.currentNotification && !root.notificationBridge.currentNotification.persistent
            onTriggered: { if (root.notificationBridge) root.notificationBridge.dismiss() }
        }
    }

    Keys.onEscapePressed: {
        if (root.notificationBridge) root.notificationBridge.dismiss()
    }
}
