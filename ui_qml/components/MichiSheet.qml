import QtQuick
import QtQuick.Controls
import "../theme"

Popup {
    id: root

    property string sheetTitle: ""
    property int sheetWidth: 360
    property int maxHeight: Math.min(400, parent ? parent.height * 0.6 : 400)
    property bool sheetOpen: false

    signal sheetClosed()

    width: sheetWidth
    height: maxHeight
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? parent.height - height - MichiTheme.spacing.xl : 0
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    visible: sheetOpen

    Accessible.role: Accessible.Dialog
    Accessible.name: sheetTitle

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: MichiTheme.motion.durationNormal; easing.type: Easing.OutCubic }
        NumberAnimation { property: "y"; from: root.y + 40; to: root.y; duration: MichiTheme.motion.durationNormal; easing.type: Easing.OutCubic }
    }

    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: MichiTheme.motion.durationFast; easing.type: Easing.InCubic }
        NumberAnimation { property: "y"; from: root.y; to: root.y + 40; duration: MichiTheme.motion.durationFast; easing.type: Easing.InCubic }
    }

    background: Rectangle {
        color: MichiTheme.colors.surfacePopup
        radius: MichiTheme.radius.xl
        border.width: 1
        border.color: MichiTheme.colors.borderCard

        Rectangle {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: 32
            height: 4
            radius: 2
            color: MichiTheme.colors.controlTrack
            anchors.topMargin: 8
        }
    }

    contentItem: Column {
        anchors.fill: parent
        anchors.topMargin: MichiTheme.spacing.xl
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        anchors.bottomMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.md

        Text {
            width: parent.width
            text: root.sheetTitle
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            visible: root.sheetTitle !== ""
        }
    }
}
