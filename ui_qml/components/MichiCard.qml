import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../materials"

Item {
    id: root
    objectName: controlObjectName
    activeFocusOnTab: interactive && enabled

    property string controlObjectName: "michiCard"
    property string title: ""
    property string subtitle: ""
    property string variant: "solid"
    property bool hovered: false
    property bool interactive: false
    property bool elevated: false
    property bool selected: false
    property bool animateInteraction: interactive
    readonly property bool pressed: cardAction.pressed
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

    MichiBaseSurface {
        id: background
        objectName: "michiCardBackground"
        anchors.fill: parent
        radius: MichiTheme.radius.md
        level: root.elevated || root.variant === "elevated" ? 3 : 2
        borderVisible: root.variant !== "ghost" || root.hovered || root.selected || root.activeFocus
        selected: root.selected || root.activeFocus
        hovered: root.hovered
        pressed: root.pressed
        enabled: root.enabled
        visible: root.variant !== "ghost" || root.hovered || root.pressed
                 || root.selected || root.activeFocus
        scale: root.pressed && root.animateInteraction ? 0.992 : 1.0
        Behavior on scale {
            NumberAnimation {
                duration: MichiTheme.motion.fast
                easing.type: MichiTheme.motion.easing.emphasis
            }
        }
    }

    MouseArea {
        id: cardAction
        objectName: "michiCardAction"
        anchors.fill: parent
        enabled: root.interactive && root.enabled
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }

    HoverHandler {
        enabled: root.interactive && root.enabled
        onHoveredChanged: root.hovered = hovered
    }

    Column {
        id: contentColumn
        z: 1
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

        Item {
            id: customContent
            width: parent.width
            height: children.length > 0 ? childrenRect.height : 0
            visible: children.length > 0
        }
    }

}
