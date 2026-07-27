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
    property bool symbolic: true
    property bool circular: false
    property bool showSelectionMarker: true
    property color symbolicColor: root.selected
                                  ? MichiTheme.colors.accentBlue
                                  : root.hovered
                                    ? MichiTheme.colors.textPrimary
                                    : MichiTheme.colors.textSecondary
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
        radius: root.circular ? width / 2 : MichiTheme.radius.md
        color: !root.enabled ? "transparent"
             : root.down ? MichiTheme.colors.surfacePressed
             : root.selected ? MichiTheme.colors.accentSurface
             : root.hovered ? MichiTheme.colors.surfaceHover : "transparent"
        border.width: root.activeFocus ? MichiTheme.focusWidth
                                      : root.selected || root.hovered ? MichiTheme.borderWidth : 0
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus
                                      : root.selected ? MichiTheme.colors.borderHover
                                                      : MichiTheme.colors.borderSubtle
        scale: root.down ? 0.97 : 1.0

        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
        Behavior on border.color { ColorAnimation { duration: MichiTheme.motion.fast } }
        Behavior on scale {
            NumberAnimation {
                duration: MichiTheme.motion.fast
                easing.type: MichiTheme.motion.easing.emphasis
            }
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 4
            width: root.selected && root.showSelectionMarker ? 14 : 0
            height: 2
            radius: 1
            color: MichiTheme.colors.accentPrimary
            visible: width > 0
            Behavior on width { NumberAnimation { duration: MichiTheme.motion.fast } }
        }
    }

    contentItem: Item {
        Image {
            anchors.centerIn: parent
            width: MichiTheme.iconSizeRegular
            height: MichiTheme.iconSizeRegular
            source: root.iconSource !== "" ? Qt.resolvedUrl(root.iconSource) : ""
            sourceSize.width: 32
            sourceSize.height: 32
            fillMode: Image.PreserveAspectFit
            opacity: root.enabled ? 1.0 : MichiTheme.opacity.disabled
            visible: root.iconSource !== "" && !root.symbolic
        }

        MichiIcon {
            anchors.centerIn: parent
            source: root.iconSource
            size: MichiTheme.iconSizeRegular
            color: root.symbolicColor
            disabled: !root.enabled
            visible: root.iconSource !== "" && root.symbolic
            accessibleName: ""
        }

        Text {
            anchors.centerIn: parent
            text: root.iconText
            font.pixelSize: MichiTheme.typography.cardTitleSize
            color: root.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
            opacity: root.enabled ? 1.0 : MichiTheme.opacity.disabled
            visible: root.iconSource === "" && root.iconText !== ""
        }
    }

    QQC2.ToolTip {
        visible: root.hovered && root.tooltipText !== ""
        text: root.tooltipText
        delay: 600
    }
}
