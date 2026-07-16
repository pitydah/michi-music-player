import QtQuick
import "../theme"

Item {
    id: root

    objectName: "michiMenuItem"

    property string itemText: ""
    property string iconText: ""
    property string shortcutText: ""
    property bool selected: false
    property bool hovered: false
    property bool loading: false
    property string accessibleName: root.itemText
    property string accessibleDescription: root.shortcutText !== "" ? root.itemText + " (" + root.shortcutText + ")" : ""

    signal triggered()

    implicitHeight: MichiTheme.density.regular
    implicitWidth: 180

    Accessible.role: Accessible.MenuItem
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.xs
        color: root.selected ? MichiTheme.colors.accentSelection
             : root.hovered ? MichiTheme.colors.surfaceHover : "transparent"
        border.width: 0
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.iconText
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            visible: root.iconText !== ""
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.itemText
            color: root.enabled ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: root.selected ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
            elide: Text.ElideRight
        }

        Item { Layout.fillWidth: true; width: 1; height: 1 }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.shortcutText
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root.shortcutText !== ""
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: root.hovered = true
        onExited: root.hovered = false
        onClicked: if (root.enabled && !root.loading) root.triggered()
    }
}
