import QtQuick
import "../theme"

Item {
    id: root

    property string key: ""
    property string value: ""
    property string meta: ""
    property bool monospace: false
    property int rowHeight: MichiTheme.density.regular

    Accessible.role: Accessible.StaticText
    Accessible.name: key + ": " + value

    implicitHeight: rowHeight

    Row {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.35
            text: root.key
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            elide: Text.ElideRight
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: root.meta !== "" ? parent.width * 0.35 : parent.width * 0.65
            text: root.value
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.family: root.monospace ? "monospace" : ""
            elide: Text.ElideRight
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.30
            text: root.meta
            color: MichiTheme.colors.textMeta
            font.pixelSize: MichiTheme.typography.captionSize
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
            visible: root.meta !== ""
        }
    }
}
