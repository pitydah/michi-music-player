import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    objectName: controlObjectName
    activeFocusOnTab: interactive && enabled

    property string controlObjectName: "michiCard"
    property string title: ""
    property string subtitle: ""
    property string variant: "solid"
    property bool hovered: false
    property bool interactive: true
    property bool elevated: false
    property bool selected: false
    property string accessibleName: title
    property string accessibleDescription: subtitle
    property alias cardRadius: background.radius
    default property alias content: customContent.data

    signal clicked()

    implicitWidth: 240
    implicitHeight: Math.max(MichiTheme.minimumInteractiveSize,
                             contentColumn.implicitHeight + MichiTheme.spacing.lg * 2)
    Accessible.role: interactive ? Accessible.Button : Accessible.Pane
    Accessible.name: accessibleName
    Accessible.description: accessibleDescription
    Accessible.onPressAction: if (interactive && enabled) clicked()
    Keys.onReturnPressed: if (interactive && enabled) clicked()
    Keys.onSpacePressed: if (interactive && enabled) clicked()

    Rectangle {
        id: background
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: {
            if (!root.enabled)
                return MichiTheme.colors.surfaceDisabled
            if (root.selected)
                return MichiTheme.colors.accentSelection
            if (root.hovered || root.activeFocus)
                return MichiTheme.colors.surfaceCardHover
            return root.elevated ? MichiTheme.colors.surfaceCardElevated
                                 : MichiTheme.colors.surfaceCard
        }
        border.width: root.activeFocus ? MichiTheme.borderWidthFocus
                                      : MichiTheme.borderWidth
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus
                                       : root.hovered ? MichiTheme.colors.borderHover
                                                      : MichiTheme.colors.borderCard
        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
        Behavior on border.color { ColorAnimation { duration: MichiTheme.motion.fast } }
    }

    Column {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.xs

        Text {
            width: parent.width
            visible: text !== ""
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.cardTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            wrapMode: Text.WordWrap
        }

        Text {
            width: parent.width
            visible: text !== ""
            text: root.subtitle
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
        }

        Column {
            id: customContent
            width: parent.width
            spacing: MichiTheme.spacing.sm
            visible: children.length > 0
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: root.interactive
        enabled: root.interactive && root.enabled
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onEntered: root.hovered = true
        onExited: root.hovered = false
        onClicked: root.clicked()
    }
}
