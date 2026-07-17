import QtQuick
import QtQuick.Controls
import "../../theme"
import "../foundations"

FocusScope {
    id: root

    property string title: ""
    property string subtitle: ""
    property bool selected: false
    property bool checked: false
    property string accessibleName: title
    property alias leadingContent: leading.data
    property alias trailingContent: trailing.data

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)
    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitHeight: MichiTheme.rowHeightComfortable
    activeFocusOnTab: enabled
    opacity: enabled ? 1.0 : MichiTheme.opacity.disabled

    Accessible.role: Accessible.ListItem
    Accessible.name: accessibleName
    Accessible.description: subtitle
    Accessible.selected: selected

    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    Rectangle {
    objectName: "michiListRow"
    focus: true
        anchors.fill: parent
        radius: MichiTheme.radius.sm
        color: root.selected ? MichiTheme.colors.accentSelection
                             : pointer.hovered ? MichiTheme.colors.surfaceHover : "transparent"
    }
    Item { id: leading; anchors.left: parent.left; width: childrenRect.width; height: parent.height }
    Column {
        anchors.left: leading.right
        anchors.right: trailing.left
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        anchors.verticalCenter: parent.verticalCenter
        Text { width: parent.width; text: root.title; color: MichiTheme.colors.textPrimary; elide: Text.ElideRight }
        Text { width: parent.width; text: root.subtitle; color: MichiTheme.colors.textSecondary; elide: Text.ElideRight; visible: text !== "" }
    }
    Item { id: trailing; anchors.right: parent.right; width: childrenRect.width; height: parent.height }
    MichiFocusRing { control: root; controlRadius: MichiTheme.radius.sm }
    HoverHandler { id: pointer }
    TapHandler { onTapped: root.clicked(); onDoubleTapped: root.doubleClicked() }
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: function(point) { root.contextRequested(point.position.x, point.position.y) }
    }
}
