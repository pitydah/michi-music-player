import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string shortcut: ""
    property string label: ""
    property string objectName: "keyboardShortcutHint"

    implicitWidth: row.implicitWidth + MichiTheme.spacing.sm * 2
    implicitHeight: row.implicitHeight + MichiTheme.spacing.xs * 2

    Accessible.role: Accessible.StaticText
    Accessible.name: root.label + (root.shortcut !== "" ? " atajo: " + root.shortcut : "")

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusXs
        color: MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.xs

        Text {
            text: root.label
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            visible: root.label !== ""
        }

        Rectangle {
            height: implicitHeight + MichiTheme.spacing.xs
            width: implicitWidth + MichiTheme.spacing.sm
            radius: MichiTheme.radiusXs
            color: MichiTheme.colors.surfaceSubtle
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle
            visible: root.shortcut !== ""

            Text {
                anchors.centerIn: parent
                text: root.shortcut
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                font.family: "monospace"
            }
        }
    }
}
