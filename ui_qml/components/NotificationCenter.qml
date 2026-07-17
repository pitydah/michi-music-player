import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    objectName: "notificationCenter"
    focus: true

    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var nb: bridge
    property bool reducedMotion: false
    property bool pinned: false
    property bool _open: false
    property var notificationItems: []
    readonly property int count: notificationItems.length
    readonly property bool hovered: hoverHandler.hovered

    signal dismissAllRequested()
    signal notificationActivated(string notificationId)

    Accessible.role: Accessible.Pane
    Accessible.name: "Centro de notificaciones"
    Accessible.description: count === 1 ? "1 notificación activa" : count + " notificaciones activas"

    implicitWidth: 360
    implicitHeight: Math.min(400, contentColumn.implicitHeight + MichiTheme.spacing.md * 2)
    visible: opacity > 0.001
    enabled: _open && count > 0
    opacity: _open && count > 0 ? 1 : 0
    scale: _open && count > 0 ? 1 : 0.98

    transform: Translate {
        x: root._open && root.count > 0 ? 0 : root.width + MichiTheme.spacing.lg
    }

    Behavior on opacity {
        NumberAnimation { duration: root.reducedMotion ? 1 : MichiTheme.motion.durationNormal }
    }
    Behavior on scale {
        NumberAnimation { duration: root.reducedMotion ? 1 : MichiTheme.motion.durationNormal }
    }

    HoverHandler {
        id: hoverHandler
        onHoveredChanged: {
            if (hovered)
                autoCloseTimer.stop()
            else if (!root.pinned && root._open)
                autoCloseTimer.restart()
        }
    }

    Timer {
        id: autoCloseTimer
        interval: 5000
        repeat: false
        onTriggered: {
            if (!root.pinned && !root.hovered)
                root._open = false
        }
    }

    function notificationId(item) {
        return item && item.id !== undefined ? String(item.id) : ""
    }

    function refresh() {
        if (!root.nb) {
            root.notificationItems = []
            root._open = false
            return
        }

        var merged = []
        var seen = ({})
        var current = root.nb.currentNotification
        if (current) {
            var currentId = root.notificationId(current)
            if (currentId !== "")
                seen[currentId] = true
            merged.push(current)
        }

        var persistent = root.nb.persistentNotifications || []
        for (var index = 0; index < persistent.length; index++) {
            var item = persistent[index]
            var itemId = root.notificationId(item)
            if (itemId !== "" && seen[itemId])
                continue
            if (itemId !== "")
                seen[itemId] = true
            merged.push(item)
        }

        root.notificationItems = merged
        if (merged.length > 0) {
            root._open = true
            if (!root.pinned && !root.hovered)
                autoCloseTimer.restart()
        } else {
            autoCloseTimer.stop()
            root._open = false
        }
    }

    function open() {
        root.refresh()
        if (root.count > 0)
            root._open = true
    }

    function close() {
        autoCloseTimer.stop()
        root._open = false
    }

    function toggle() {
        if (root._open)
            root.close()
        else
            root.open()
    }

    function clearAll() {
        if (root.nb && typeof root.nb.clear === "function")
            root.nb.clear()
        root.notificationItems = []
        root._open = false
        root.dismissAllRequested()
    }

    Connections {
        target: root.nb
        function onNotificationChanged() { root.refresh() }
        function onNotificationCountChanged() { root.refresh() }
    }

    Component.onCompleted: root.refresh()

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        ColumnLayout {
            id: contentColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.sm

                Text {
                    Layout.fillWidth: true
                    text: "Notificaciones"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                StatusBadge {
                    text: String(root.count)
                    kind: root.count > 0 ? "info" : "disconnected"
                    visible: root.count > 0
                }

                MichiButton {
                    text: root.pinned ? "Fijado" : "Fijar"
                    variant: "ghost"
                    onClicked: {
                        root.pinned = !root.pinned
                        if (root.pinned)
                            autoCloseTimer.stop()
                        else if (root._open)
                            autoCloseTimer.restart()
                    }
                }

                MichiButton {
                    text: "Limpiar"
                    variant: "ghost"
                    enabled: root.count > 0
                    onClicked: root.clearAll()
                }

                MichiButton {
                    text: "Cerrar"
                    variant: "ghost"
                    onClicked: root.close()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            ListView {
                id: notificationList
                Layout.fillWidth: true
                Layout.fillHeight: true
                implicitHeight: Math.min(contentHeight, 320)
                clip: true
                spacing: MichiTheme.spacing.sm
                model: root.notificationItems
                boundsBehavior: Flickable.StopAtBounds

                delegate: NotificationItem {
                    required property var modelData
                    width: notificationList.width
                    notification: modelData
                    bridge: root.nb
                    reducedMotion: root.reducedMotion
                    onDismissed: root.refresh()
                    onActionTriggered: function(actionId) {
                        root.notificationActivated(root.notificationId(modelData))
                        root.refresh()
                    }
                }

                QQC2.ScrollBar.vertical: QQC2.ScrollBar { policy: QQC2.ScrollBar.AsNeeded }
            }

            Text {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.count === 0
                text: "No hay notificaciones"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    Keys.onEscapePressed: root.close()
}
