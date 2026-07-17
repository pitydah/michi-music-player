import QtQuick
import "../theme"

Rectangle {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string tooltipText: ""
    property Item target: null
    property int showDelay: 600
    property int hideDelay: 100
    property string position: "top"
    property string accessibleName: root.tooltipText
    property string accessibleDescription: ""

    visible: false
    opacity: 0

    Accessible.role: Accessible.ToolTip
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    radius: MichiTheme.radius.sm
    color: MichiTheme.colors.surfacePopup
    border.width: MichiTheme.borderWidth
    border.color: MichiTheme.colors.borderCard

    implicitHeight: label.implicitHeight + MichiTheme.spacing.sm * 2
    implicitWidth: Math.max(40, label.implicitWidth + MichiTheme.spacing.md * 2)

    Text {
        id: label
        anchors.centerIn: parent
        text: root.tooltipText
        color: MichiTheme.colors.textPrimary
        font.pixelSize: MichiTheme.typography.captionSize
        font.weight: MichiTheme.typography.weightMedium
    }

    Timer {
        id: showTimer
        interval: root.showDelay
        onTriggered: {
            root._positionAndShow()
        }
    }

    Timer {
        id: hideTimer
        interval: root.hideDelay
        onTriggered: {
            root.visible = false
            root.opacity = 0
        }
    }

    function _positionAndShow() {
        if (!root.target) return
        var pos = root.target.mapToItem(null, 0, 0)
        var w = root.implicitWidth
        var h = root.implicitHeight

        switch (root.position) {
            case "top":
                root.x = pos.x + (root.target.width - w) / 2
                root.y = pos.y - h - MichiTheme.spacing.xs
                break
            case "bottom":
                root.x = pos.x + (root.target.width - w) / 2
                root.y = pos.y + root.target.height + MichiTheme.spacing.xs
                break
            case "left":
                root.x = pos.x - w - MichiTheme.spacing.xs
                root.y = pos.y + (root.target.height - h) / 2
                break
            case "right":
                root.x = pos.x + root.target.width + MichiTheme.spacing.xs
                root.y = pos.y + (root.target.height - h) / 2
                break
        }

        root.visible = true
        root.opacity = 1
    }

    function show(targetItem) {
        if (targetItem) root.target = targetItem
        hideTimer.stop()
        showTimer.restart()
    }

    function hide() {
        showTimer.stop()
        hideTimer.restart()
    }

    Behavior on opacity {
        NumberAnimation { duration: MichiTheme.motion.fast }
    }
}
