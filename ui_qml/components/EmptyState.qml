import QtQuick
import "../theme"

Item {
    id: root

    property string iconText: ""
    property string title: ""
    property string subtitle: ""
    property string actionText: ""
    property bool showAction: false
    property string objectName: "emptyState"

    signal actionClicked()

    Accessible.role: Accessible.StaticText
    Accessible.name: root.title
    Accessible.description: root.subtitle

    Keys.onReturnPressed: {
        if (root.showAction && root.actionText !== "") root.actionClicked()
    }
    Keys.onSpacePressed: {
        if (root.showAction && root.actionText !== "") root.actionClicked()
    }

    Column {
        spacing: MichiTheme.spacing.md
        anchors.centerIn: parent

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.iconText
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.heroTitleSize
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
            opacity: MichiTheme.opacityActive
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
            Accessible.name: root.actionText
        }
    }
}
