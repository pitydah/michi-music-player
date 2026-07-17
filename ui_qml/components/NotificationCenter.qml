import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    objectName: "notificationCenter"
    focus: true
    id: root

    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var nb: bridge
    property var notifications: []
    property var persistentNotifications: []
    property bool reducedMotion: false

    signal dismissAllRequested()
    signal notificationActivated(string notificationId)

    Accessible.role: Accessible.Pane
    Accessible.name: "Centro de notificaciones"
    Accessible.description: "Lista de notificaciones activas"

    color: MichiTheme.colors.surfacePopup
    radius: MichiTheme.radiusLg
    border.width: MichiTheme.borderWidth
    border.color: MichiTheme.colors.borderCard

    clip: true

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            width: parent.width
            height: 48
            color: "transparent"

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Centro de notificaciones"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { width: 1; height: 1 }

                MichiButton {
                    Accessible.role: Accessible.Button

                    id: dismissAllBtn
                    activeFocusOnTab: true

                    anchors.verticalCenter: parent.verticalCenter
                    text: "Descartar todas"
                    variant: "ghost"
                    visible: (root.notifications.length > 0 || root.persistentNotifications.length > 0)
                    onClicked: {
                        if (root.bridge) root.bridge.clear()
                        root.dismissAllRequested()
                    }

                    Accessible.description: "Eliminar todas las notificaciones activas"
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Item {
            id: emptyStateItem
            width: parent.width
            height: parent.height - 48 - 1
            visible: root.notifications.length === 0 && root.persistentNotifications.length === 0

            EmptyState {
                anchors.centerIn: parent
                iconText: "\uD83D\uDD14"
                title: "Sin notificaciones"
                subtitle: "No hay notificaciones activas en este momento"
                visible: emptyStateItem.visible
            }
        }
            Accessible.role: Accessible.List

            Accessible.name: "ListView"

            activeFocusOnTab: true


        ListView {
            focusPolicy: Qt.StrongFocus
            id: notificationList
            width: parent.width
            height: parent.height - 48 - 1
            model: {
                const all = []
                for (let i = 0; i < root.persistentNotifications.length; i++) {
                    const n = root.persistentNotifications[i]
                    all.push(n)
                }
                for (let i = 0; i < root.notifications.length; i++) {
                    all.push(root.notifications[i])
                }
                return all
            }
            visible: !emptyStateItem.visible
            clip: true
            focus: true
            keyNavigationEnabled: true
            highlightMoveDuration: root.reducedMotion ? 1 : MichiTheme.motion.fast


            delegate: Item {
                id: delegateRoot
                width: notificationList.width
                height: {
                    if (modelData.kind === "progress") return 120
                    return 80
                }

                Rectangle {
                    id: sectionHeader
                    width: parent.width
                    height: 28
                    color: "transparent"
                    visible: {
                        if (index === 0) return true
                        const prev = notificationList.model[index - 1]
                        if (!prev || !modelData) return false
                        const prevPersistent = prev.persistent || prev.kind === "error" || prev.kind === "progress"
                        const currPersistent = modelData.persistent || modelData.kind === "error" || modelData.kind === "progress"
                        return prevPersistent !== currPersistent
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.verticalCenter: parent.verticalCenter
                        text: {
                            const isPersistent = modelData.persistent || modelData.kind === "error" || modelData.kind === "progress"
                            return isPersistent ? "PERSISTENTES" : "NOTIFICACIONES"
                        }
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.badgeSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }
                }

                Loader {
                    anchors.fill: parent
                    anchors.topMargin: sectionHeader.visible ? sectionHeader.height : 0
                    sourceComponent: {
                        if (modelData.kind === "progress") return progressItemComponent
                        return notificationItemComponent
                    }

                    onLoaded: {
                        item.notification = modelData
                        item.bridge = root.bridge
                        item.reducedMotion = root.reducedMotion
                        item.dismissed.connect(function() {
                            notificationList.currentIndex = -1
                        })
                        item.actionTriggered.connect(function(actionId) {
                            root.notificationActivated(modelData.id || "")
                        })
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: MichiTheme.colors.borderSubtle
                }
            }

            highlight: Rectangle {
                color: MichiTheme.colors.surfaceHover
                radius: MichiTheme.radius.sm
            }

            Keys.onUpPressed: {
                if (notificationList.currentIndex > 0) notificationList.currentIndex--
            }
            Keys.onDownPressed: {
                if (notificationList.currentIndex < notificationList.count - 1) notificationList.currentIndex++
            }
            Keys.onReturnPressed: {
                const item = notificationList.currentItem
                if (item && item.children[1] && item.children[1].item) {
                    item.children[1].item.activatePrimaryAction()
                }
            }
            Keys.onEnterPressed: {
                const item = notificationList.currentItem
                if (item && item.children[1] && item.children[1].item) {
                    item.children[1].item.activatePrimaryAction()
                }
            }
            Keys.onEscapePressed: root.visible = false
        }
    }

    Component {
        id: notificationItemComponent
        NotificationItem {}
    }

    Component {
        id: progressItemComponent
        NotificationProgressItem {}
    }

    function refresh() {
        if (root.bridge) {
            const current = root.bridge.currentNotification
            const all = []
            if (current) all.push(current)
            root.notifications = root.bridge.queueLength > 0 ? [] : []
            root.persistentNotifications = root.bridge.persistentNotifications || []
        }
    }

    Timer {
        interval: 1000
        running: root.visible
        repeat: true
        onTriggered: root.refresh()
    }
}
