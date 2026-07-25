import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../foundations"
import ".."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Header"
    objectName: "michiPageHeader"
    focus: true
    id: root

    property string title: ""
    property string subtitle: ""
    property string iconKey: ""
    property alias actions: actionHost.data
    property alias tabs: tabsHost.data
    readonly property real topHeight: Math.max(titleColumn.implicitHeight,
                                                actionHost.childrenRect.height,
                                                sectionIcon.visible ? sectionIcon.height : 0)

    implicitHeight: topHeight + (tabsHost.visible ? MichiTheme.spacing.md + tabsHost.childrenRect.height : 0)

    MichiResponsive { id: responsive; availableWidth: root.width }

    MichiIcon {
        id: sectionIcon
        anchors.left: parent.left
        anchors.top: parent.top
        iconKey: root.iconKey
        size: 32
        active: true
        visible: root.iconKey !== ""
        accessibleName: root.title
    }

    Column {
        id: titleColumn
        anchors.left: sectionIcon.visible ? sectionIcon.right : parent.left
        anchors.leftMargin: sectionIcon.visible ? MichiTheme.spacing.md : 0
        anchors.right: responsive.compact ? parent.right : actionHost.left
        anchors.rightMargin: responsive.compact ? 0 : MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.xs

        Text {
            width: parent.width
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.pageTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: root.subtitle
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            visible: text !== ""
        }
    }

    Row {
        id: actionHost
        anchors.right: parent.right
        anchors.top: responsive.compact ? titleColumn.bottom : parent.top
        anchors.topMargin: responsive.compact ? MichiTheme.spacing.md : 0
        spacing: MichiTheme.spacing.sm
    }

    Item {
        id: tabsHost
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: root.topHeight + MichiTheme.spacing.md
        height: childrenRect.height
        visible: children.length > 0
    }
}
