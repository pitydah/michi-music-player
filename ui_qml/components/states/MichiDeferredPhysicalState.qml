import QtQuick
import "../../theme"

Item {
    id: root

    property string title: "Requiere hardware físico"
    property string message: "Esta funcionalidad necesita hardware físico especializado que no está presente."
    property string details: ""
    property string iconText: "\u2699"

    objectName: "DeferredPhysicalState"

    Accessible.role: Accessible.AlertMessage
    Accessible.name: title
    Accessible.description: message + (details ? ". " + details : "")

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.iconText || "\u2699"
            color: MichiTheme.colors.textMuted
            font.pixelSize: 36
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(implicitWidth, 460)
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.details
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }
    }
}
