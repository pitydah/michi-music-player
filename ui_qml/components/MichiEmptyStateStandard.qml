import QtQuick
import "../theme"

Column {
    id: root

    property string title: "Sin contenido"
    property string message: ""
    property string actionText: ""
    property string secondaryActionText: ""
    property string iconText: ""
    property bool busy: false

    signal actionClicked()
    signal secondaryActionClicked()

    Accessible.role: Accessible.StaticText
    Accessible.name: root.title
    Accessible.description: root.message

    spacing: MichiTheme.spacing.md
    anchors.centerIn: parent
    width: Math.min(implicitWidth, 400)

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.iconText
        color: MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.heroTitleSize
        visible: root.iconText !== ""
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        text: root.title
        color: MichiTheme.colors.textPrimary
        font.pixelSize: MichiTheme.typography.sectionTitleSize
        font.weight: MichiTheme.typography.weightMedium
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        text: root.message
        color: MichiTheme.colors.textSecondary
        font.pixelSize: MichiTheme.typography.bodySize
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        visible: root.message !== ""
    }

    MichiProgressBar {
        anchors.horizontalCenter: parent.horizontalCenter
        width: 160
        indeterminate: true
        visible: root.busy
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: MichiTheme.spacing.sm
        visible: root.actionText !== "" || root.secondaryActionText !== ""

        MichiButton {
            text: root.actionText
            visible: text !== ""
            onClicked: root.actionClicked()
        }

        MichiButton {
            text: root.secondaryActionText
            variant: "ghost"
            visible: text !== ""
            onClicked: root.secondaryActionClicked()
        }
    }
}
