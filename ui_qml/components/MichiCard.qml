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
    property bool interactive: false
    property bool elevated: false
    property bool selected: false
    readonly property bool pressed: cardAction.pressed
    property string accessibleName: title
    property string accessibleDescription: subtitle
    property alias cardRadius: background.radius
    default property alias content: customContent.data

    signal clicked()

    function baseColor() {
        if (variant === "accent") return MichiTheme.colors.accentSurface
        if (variant === "info") return MichiTheme.colors.badgeInfoBg
        if (variant === "success") return MichiTheme.colors.badgeActiveBg
        if (variant === "warning") return MichiTheme.colors.badgeWarningBg
        if (variant === "danger" || variant === "error") return MichiTheme.colors.badgeDangerBg
        if (variant === "elevated" || elevated) return MichiTheme.colors.surfaceCardElevated
        return MichiTheme.colors.surfaceCard
    }

    function baseBorderColor() {
        if (variant === "accent") return MichiTheme.colors.borderActive
        if (variant === "info") return MichiTheme.colors.info
        if (variant === "success") return MichiTheme.colors.success
        if (variant === "warning") return MichiTheme.colors.warning
        if (variant === "danger" || variant === "error") return MichiTheme.colors.borderError
        return MichiTheme.colors.borderCard
    }

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
        objectName: "michiCardBackground"
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: {
            if (!root.enabled)
                return MichiTheme.colors.surfaceDisabled
            if (root.selected)
                return MichiTheme.colors.accentSelection
            if (root.pressed)
                return MichiTheme.colors.surfacePressed
            if (root.hovered || root.activeFocus)
                return MichiTheme.colors.surfaceCardHover
            return root.baseColor()
        }
        border.width: root.activeFocus ? MichiTheme.borderWidthFocus
                                      : MichiTheme.borderWidth
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus
                                       : root.hovered ? MichiTheme.colors.borderHover
                                                      : root.baseBorderColor()
        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
        Behavior on border.color { ColorAnimation { duration: MichiTheme.motion.fast } }
    }

    Rectangle {
        anchors.fill: background
        anchors.margins: MichiTheme.borderWidth
        radius: Math.max(0, background.radius - MichiTheme.borderWidth)
        color: "transparent"
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderInner
        visible: root.variant === "glass"
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

        Column {
            id: customContent
            width: parent.width
            spacing: MichiTheme.spacing.sm
            visible: children.length > 0
        }
    }

}
