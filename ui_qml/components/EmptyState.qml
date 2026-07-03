import QtQuick
import "../theme"

Column {
    id: root

    property string iconText: ""
    property string title: ""
    property string subtitle: ""
    property string actionText: ""
    property bool showAction: false

    signal actionClicked()

    spacing: MichiTheme.spacing.md
    anchors.centerIn: parent ? undefined : undefined

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.iconText
        color: MichiTheme.colors.textMuted
        font.pixelSize: 36
        visible: root.iconText !== ""
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.title
        color: MichiTheme.colors.textPrimary
        font.pixelSize: MichiTheme.typography.sectionTitleSize
        font.weight: MichiTheme.typography.weightMedium
        horizontalAlignment: Text.AlignHCenter
        opacity: MichiTheme.opacityHover
        visible: root.title !== ""
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.subtitle
        color: MichiTheme.colors.textSecondary
        font.pixelSize: MichiTheme.typography.bodySize
        horizontalAlignment: Text.AlignHCenter
        opacity: 0.56
        width: Math.min(implicitWidth, 400)
        wrapMode: Text.WordWrap
        visible: root.subtitle !== ""
    }

    MichiButton {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.actionText
        variant: "primary"
        visible: root.showAction && root.actionText !== ""
        onClicked: root.actionClicked()
    }
}
