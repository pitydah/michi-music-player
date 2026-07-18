import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    objectName: "notificationCenter"
    focus: true
    id: root

    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var nb: bridge
    property bool reducedMotion: false
    property bool pinned: false

    signal dismissAllRequested()
    signal notificationActivated(string notificationId)

    ListModel { id: notificationModel }

    Accessible.role: Accessible.Pane
    Accessible.name: "Centro de notificaciones"
    Accessible.description: "Lista de notificaciones activas"

    implicitWidth: 360
    visible: (notificationModel.count > 0 || root.pinned) && _open

    property bool _open: false
    property int _autoCloseTimer: 0

    function open() {
        _open = true
        root.refresh()
        if (!root.pinned) {
            _autoCloseTimer = Qt.callLater(function() {
                Qt.callLater(function() {
                    if (!root.containsMouse && !root.pinned)
                        _open = false
                })
            }, 5000)
        }
    }

    function close() {
        _open = false
        if (_autoCloseTimer) {
            Qt.callLater(function() { _autoCloseTimer = 0 }, 0)
        }
    }

    function toggle() {
        if (_open) close()
        else open()
    }

    x: parent ? parent.width : 0
    y: MichiTheme.headerHeight + MichiTheme.spacing.sm
    width: 360
    height: Math.min(420, parent ? parent.height * 0.55 : 420)
    z: 9997

    NumberAnimation on x {
        id: slideAnim
        from: root.parent ? root.parent.width : 0
        to: root.parent ? root.parent.width - root.width - MichiTheme.spacing.md : root.width
        duration: root.reducedMotion ? 0 : MichiTheme.motion.durationNormal
        easing.type: Easing.OutCubic
        running: false
    }

    on_OpenChanged: {
        if (_open) {
            slideAnim.from = root.parent ? root.parent.width : 0
            slideAnim.to = root.parent ? root.parent.width - root.width - MichiTheme.spacing.md : root.width
            slideAnim.start()
            root.visible = true
        } else {
            slideAnim.from = root.parent ? root.parent.width - root.width - MichiTheme.spacing.md : root.width
            slideAnim.to = root.parent ? root.parent.width : 0
            slideAnim.start()
        }
    }

    Rectangle {
        anchors.fill: parent
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
                    anchors.leftMargin: MichiTheme.spacing.md
                    anchors.rightMargin: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("Notificaciones")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("(%1").arg(notificationModel.count + ")"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        visible: notificationModel.count > 0
                    }

                    Item { width: parent.width * 0.3; height: 1 }

                    MichiIconButton {
                        id: pinBtn
                        anchors.verticalCenter: parent.verticalCenter
                        iconSource: ""
                        iconText: root.pinned ? "\u{1F4CC}" : "\u{1F4CC}"
                        tooltipText: root.pinned ? "Desfijar" : "Fijar"
                        btnSize: 28
                        opacity: root.pinned ? 1.0 : 0.5
                        onClicked: root.pinned = !root.pinned
                    }

                    MichiIconButton {
                        id: dismissAllBtn
                        anchors.verticalCenter: parent.verticalCenter
                        iconText: "\u2716"
                        tooltipText: "Descartar todas"
                        btnSize: 28
                        visible: notificationModel.count > 0
                        onClicked: {
                            notificationModel.clear()
                            if (root.bridge) root.bridge.clear()
                            if (root.nb) root.nb.clear()
                            root.dismissAllRequested()
                        }
                    }

                    MichiIconButton {
                        anchors.verticalCenter: parent.verticalCenter
                        iconText: "\u2715"
                        tooltipText: "Cerrar"
                        btnSize: 28
                        onClicked: root.close()
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
                visible: notificationModel.count === 0

                Column {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md
                    width: Math.min(implicitWidth, parent.width * 0.8)

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: qsTr("\u2709")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: 32
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: qsTr("Sin notificaciones")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width
                        text: qsTr("No hay notificaciones activas")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }

                    MichiButton {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: qsTr("Cerrar")
                        variant: "ghost"
                        onClicked: root.close()
                    }
                }
            }

            ListView {
                id: notificationList
                width: parent.width
                height: parent.height - 48 - 1
                model: notificationModel
                visible: notificationModel.count > 0
                clip: true
                focus: true
                keyNavigationEnabled: true
                highlightMoveDuration: root.reducedMotion ? 1 : MichiTheme.motion.fast
                boundsBehavior: Flickable.StopAtBounds

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
                            var prev = notificationList.model[index - 1]
                            if (!prev || !modelData) return false
                            return (prev.kind || "") !== (modelData.kind || "")
                        }

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: MichiTheme.spacing.md
                            anchors.verticalCenter: parent.verticalCenter
                            text: {
                                if (!modelData || !modelData.kind) return "NOTIFICACIONES"
                                if (modelData.kind === "error") return "Errores"
                                if (modelData.kind === "warning") return "Advertencias"
                                return "Información"
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
                    var item = notificationList.currentItem
                    if (item && item.children[1] && item.children[1].item)
                        item.children[1].item.activatePrimaryAction()
                }
                Keys.onEscapePressed: root.close()
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        propagateComposedEvents: true
        hoverEnabled: true
        onPressed: function(mouse) {
            mouse.accepted = false
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
        var persistent = root.bridge.persistentNotifications || []
        var current = root.bridge.currentNotification

        for (var i = 0; i < persistent.length; i++) {
            notificationModel.append(persistent[i])
        }
        if (current) {
            notificationModel.append(current)
        }

        if (notificationModel.count > 0 && !root._open && !root.reducedMotion) {
            _open = true
        }
    }

    Connections {
        target: root.bridge
        function onNotificationChanged() {
            root.refresh()
            if (!root._open) {
                _open = true
                if (!root.pinned) {
                    Qt.callLater(function() {
                        Qt.callLater(function() {
                            if (!root.containsMouse && !root.pinned)
                                _open = false
                        })
                    }, 5000)
                }
            }
        }
    }

    function showTemporary(message, kind, duration) {
        if (!message) return
        refresh()
        if (!root._open) {
            _open = true
        }
        if (duration > 0 && !root.pinned) {
            Qt.callLater(function() {
                Qt.callLater(function() {
                    if (!root.containsMouse && !root.pinned)
                        _open = false
                })
            }, duration)
        }
    }
}
