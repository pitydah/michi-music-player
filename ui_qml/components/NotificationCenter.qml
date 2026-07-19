import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
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

    property var notificationItems: []
    readonly property int count: notificationItems.length

    Accessible.role: Accessible.Pane
    Accessible.name: "Centro de notificaciones"
    Accessible.description: "Lista de notificaciones activas"

    implicitWidth: 360
    visible: opacity > 0.001
    enabled: _open && count > 0

    property bool _open: false
    property bool _hovered: false

    Timer {
        id: autoCloseTimer
        interval: 5000
        repeat: false
        onTriggered: {
            if (!root._hovered && !root.pinned)
                root.close()
        }
    }

    function open() {
        _open = true
        root.refresh()
        if (!root.pinned)
            autoCloseTimer.restart()
    }

    function close() {
        _open = false
        autoCloseTimer.stop()
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

    opacity: 0
    Behavior on opacity {
        enabled: !root.reducedMotion
        PropertyAnimation { duration: MichiTheme.motion.durationNormal }
    }

    on_OpenChanged: {
        if (_open) {
            opacity = 1
        } else {
            opacity = 0
        }
    }

    HoverHandler {
        id: hoverHandler
        onHoveredChanged: {
            root._hovered = hoverHandler.hovered
            if (hoverHandler.hovered)
                autoCloseTimer.stop()
            else if (_open && !root.pinned)
                autoCloseTimer.restart()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfacePopup
        radius: MichiTheme.radius.lg
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                Layout.leftMargin: MichiTheme.spacing.md
                Layout.rightMargin: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.sm

                Label {
                    text: qsTr("Notificaciones")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Layout.alignment: Qt.AlignVCenter
                }

                StatusBadge {
                    Layout.alignment: Qt.AlignVCenter
                    visible: root.count > 0
                    text: String(root.count)
                    kind: root.count > 0 ? "info" : "disconnected"
                }

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: root.pinned ? qsTr("Fijado") : qsTr("Fijar")
                    variant: "ghost"
                    onClicked: root.pinned = !root.pinned
                    Layout.alignment: Qt.AlignVCenter
                }

                MichiButton {
                    text: qsTr("Limpiar")
                    variant: "ghost"
                    visible: root.count > 0
                    onClicked: root.clearAll()
                    Layout.alignment: Qt.AlignVCenter
                }

                MichiButton {
                    text: qsTr("Cerrar")
                    variant: "ghost"
                    onClicked: root.close()
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: MichiTheme.colors.borderSubtle
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.count === 0

                Label {
                    anchors.centerIn: parent
                    text: qsTr("No hay notificaciones")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            ListView {
                id: notificationList
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: root.notificationItems
                visible: root.count > 0
                clip: true
                focus: true
                keyNavigationEnabled: true
                highlightMoveDuration: root.reducedMotion ? 1 : MichiTheme.motion.fast
                boundsBehavior: Flickable.StopAtBounds

                delegate: Item {
                    id: delegateRoot
                    width: notificationList.width
                    height: modelData.kind === "progress" ? 120 : 80

                    Rectangle {
                        id: sectionHeader
                        width: parent.width
                        height: 28
                        color: "transparent"
                        visible: {
                            if (index === 0) return true
                            var items = root.notificationItems
                            var prev = items[index - 1]
                            if (!prev || !modelData) return false
                            return (prev.kind || "") !== (modelData.kind || "")
                        }

                        Label {
                            anchors.left: parent.left
                            anchors.leftMargin: MichiTheme.spacing.md
                            anchors.verticalCenter: parent.verticalCenter
                            text: {
                                if (!modelData || !modelData.kind) return "NOTIFICACIONES"
                                if (modelData.kind === "error") return qsTr("Errores")
                                if (modelData.kind === "warning") return qsTr("Advertencias")
                                return qsTr("Información")
                            }
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.badgeSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }
                    }

                    Loader {
                        anchors.fill: parent
                        anchors.topMargin: sectionHeader.visible ? sectionHeader.height : 0
                        sourceComponent: modelData.kind === "progress"
                            ? progressItemComponent
                            : notificationItemComponent

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

                    Label {
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
        var persistent = root.bridge.persistentNotifications || []
        var current = root.bridge.currentNotification
        var merged = []
        var seen = {}
        for (var i = 0; i < persistent.length; i++) {
            var item = persistent[i]
            var itemId = item.id || ""
            if (itemId && !seen[itemId]) {
                merged.push(item)
                seen[itemId] = true
            } else if (!itemId) {
                merged.push(item)
            }
        }
        if (current) {
            var curId = current.id || ""
            if (!curId || !seen[curId])
                merged.push(current)
        }
        root.notificationItems = merged

        if (root.count > 0 && !root._open && !root.reducedMotion) {
            _open = true
        }
    }

    function clearAll() {
        root.notificationItems = []
        _open = false
        if (root.bridge) root.bridge.clear()
        root.dismissAllRequested()
    }

    Connections {
        target: root.bridge
        function onNotificationChanged() { root.refresh() }
        function onNotificationCountChanged() { root.refresh() }
    }

    Component.onCompleted: root.refresh()
}
