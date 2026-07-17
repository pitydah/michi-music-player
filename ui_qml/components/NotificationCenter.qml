import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    objectName: "notificationCenter"
    focus: true
    id: root

    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var nb: bridge
    ListModel { id: notificationModel }
    property var notifications: []
    property var persistentNotifications: []
    property bool reducedMotion: false
    Keys.onEscapePressed: { if (root.visible) root.close() }

    signal dismissAllRequested()
    signal notificationActivated(string notificationId)

    Accessible.role: Accessible.Pane
    Accessible.name: "Centro de notificaciones"
    Accessible.description: "Lista de notificaciones activas"

    color: MichiTheme.colors.surfacePopup
    radius: MichiTheme.radius.lg
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
                    visible: notificationModel.count > 0
                    onClicked: {
                        notificationModel.clear()
                        if (root.bridge) root.bridge.clear()
                        if (root.nb) root.nb.clear()
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
                title: "Sin notificaciones"
                subtitle: "No hay notificaciones activas en este momento"
                visible: emptyStateItem.visible
                Accessible.name: "Sin notificaciones"
                Accessible.description: "No hay notificaciones activas"
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
            model: notificationModel
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
                        const prevKind = prev.kind || ""
                        const currKind = modelData.kind || ""
                        return prevKind !== currKind
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.verticalCenter: parent.verticalCenter
                        text: {
                            if (!modelData || !modelData.kind) return "NOTIFICACIONES"
                            if (modelData.kind === "error") return "Errores"
                            if (modelData.kind === "warning") return "Advertencias"
                            return "Info"
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

                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: MichiTheme.spacing.md
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: MichiTheme.spacing.xs
                    text: {
                        if (!modelData || !modelData.timestamp) return ""
                        var elapsed = Math.round((Date.now() / 1000) - modelData.timestamp)
                        if (elapsed < 60) return elapsed + "s"
                        if (elapsed < 3600) return Math.floor(elapsed / 60) + "m"
                        return Math.floor(elapsed / 3600) + "h"
                    }
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
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
        if (!root.bridge) return
        notificationModel.clear()
        const persistent = root.bridge.persistentNotifications || []
        const current = root.bridge.currentNotification
        const queue = root.bridge.queueLength > 0 ? [] : []
        root.notifications = queue
        root.persistentNotifications = persistent
        for (let i = 0; i < persistent.length; i++) {
            notificationModel.append(persistent[i])
        }
        if (current) {
            notificationModel.append(current)
        }
    }

    Timer {
        interval: 1000
        running: root.visible
        repeat: true
        onTriggered: root.refresh()
    }
}
