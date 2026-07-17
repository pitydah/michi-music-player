import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Keyboard Shortcut Hint"
    objectName: "keyboardShortcutHint"
    focus: true
    id: root

    property string label: ""
    property string shortcut: ""
    property string description: ""
    property string variant: "info"
    property int shortcutSize: MichiTheme.typography.badgeSize


    Accessible.description: description || label + " atajo de teclado " + shortcut

    implicitHeight: row.implicitHeight + MichiTheme.spacing.xs * 2
    implicitWidth: row.implicitWidth + MichiTheme.spacing.sm * 2
    radius: MichiTheme.radius.sm
    color: MichiTheme.colors.surfaceCard

    border.width: MichiTheme.borderWidth
    border.color: MichiTheme.colors.borderInner

    visible: label !== "" || shortcut !== ""

    Row {
        id: row
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.xs

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            color: MichiTheme.colors.textMuted
            font.pixelSize: root.shortcutSize
            font.weight: MichiTheme.typography.weightMedium
            visible: text !== ""
        }

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            height: rowItem.implicitHeight + MichiTheme.spacing.xs
            width: rowItem.implicitWidth + MichiTheme.spacing.sm * 2
            radius: MichiTheme.radius.xs
            color: MichiTheme.colors.surfaceSubtle
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderInner
            visible: root.shortcut !== ""

            Text {
                id: rowItem
                anchors.centerIn: parent
                text: root.shortcut
                color: MichiTheme.colors.textSecondary
                font.pixelSize: root.shortcutSize
                font.weight: MichiTheme.typography.weightMedium
            }
        }

        QQC2.ToolTip {
            visible: root.hovered && root.description !== ""
            text: root.description || root.label + " (" + root.shortcut + ")"
            delay: 600
        }
    }
}
