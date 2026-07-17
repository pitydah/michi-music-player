import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

QQC2.Button {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string iconText: ""
    property string iconSource: ""
    property string tooltipText: ""
    property bool selected: false
    property int btnSize: MichiTheme.minimumInteractiveSize
    property string accessibleName: tooltipText
    property string accessibleDescription: tooltipText

    implicitWidth: Math.max(btnSize, MichiTheme.minimumInteractiveSize)
    implicitHeight: width
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    activeFocusOnTab: enabled

    Accessible.role: Accessible.Button
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    background: Rectangle {
        radius: MichiTheme.radius.pill
        color: !root.enabled ? "transparent"
             : root.down ? MichiTheme.colors.surfacePressed
             : root.selected ? MichiTheme.colors.accentSurface
             : root.hovered ? MichiTheme.colors.surfaceHover : "transparent"
        border.width: root.activeFocus ? MichiTheme.focusWidth : 0
        border.color: MichiTheme.colors.borderFocus
    }

    contentItem: Item {
        Image {
            anchors.centerIn: parent
            width: 18
            height: 18
            source: root.iconSource !== "" ? Qt.resolvedUrl(root.iconSource) : ""
            visible: root.iconSource !== ""
            sourceSize.width: 32
            sourceSize.height: 32
            fillMode: Image.PreserveAspectFit
            opacity: root.enabled ? 1.0 : MichiTheme.disabledOpacity
        }

        Text {
            anchors.centerIn: parent
            text: root.iconText
            font.pixelSize: MichiTheme.typography.cardTitleSize
            color: root.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
            opacity: root.enabled ? 1.0 : MichiTheme.disabledOpacity
            visible: root.iconSource === "" && root.iconText !== ""
        }
    }

    QQC2.ToolTip {
        visible: root.hovered && root.tooltipText !== ""
        text: root.tooltipText
        delay: 600
    }
}
