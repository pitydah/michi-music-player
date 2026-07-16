import QtQuick
import QtQuick.Controls
import "../theme"
import "foundations"

FocusScope {
    id: root

    objectName: "michiListRow"

    property string title: ""
    property string subtitle: ""
    property bool selected: false
    property bool checked: false
    property bool loading: false
    property string accessibleName: root.title
    property alias leadingContent: leading.data
    property alias trailingContent: trailing.data

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)
    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitHeight: MichiTheme.rowHeightComfortable
    activeFocusOnTab: enabled
    opacity: root.enabled ? 1.0 : MichiTheme.disabledOpacity

    Accessible.role: Accessible.ListItem
    Accessible.name: root.accessibleName
    Accessible.description: root.subtitle
    Accessible.selected: root.selected

    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.sm
        color: root.selected ? MichiTheme.colors.accentSelection
                             : pointer.hovered ? MichiTheme.colors.surfaceHover : "transparent"
        border.width: 0
    }

    Item {
        id: leading
        anchors.left: parent.left
        width: childrenRect.width
        height: parent.height
    }

    Column {
        anchors.left: leading.right
        anchors.right: trailing.left
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        anchors.verticalCenter: parent.verticalCenter

        Text {
            width: parent.width
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            elide: Text.ElideRight
            visible: root.title !== ""
        }

        Text {
            width: parent.width
            text: root.subtitle
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.secondarySize
            elide: Text.ElideRight
            visible: root.subtitle !== ""
        }
    }

    Item {
        id: trailing
        anchors.right: parent.right
        width: childrenRect.width
        height: parent.height
    }

    MichiFocusRing {
        control: root
        controlRadius: MichiTheme.radius.sm
    }

    HoverHandler { id: pointer }

    TapHandler {
        onTapped: if (!root.loading) root.clicked()
        onDoubleTapped: if (!root.loading) root.doubleClicked()
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: function(point) {
            if (!root.loading)
                root.contextRequested(point.position.x, point.position.y)
        }
    }
}
