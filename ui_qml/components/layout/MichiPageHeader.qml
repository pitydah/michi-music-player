import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../foundations"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Header"
    objectName: "michiPageHeader"
    focus: true
    id: root

    property string title: ""
    property string subtitle: ""
    property alias actions: actionHost.data

    implicitHeight: Math.max(titleColumn.implicitHeight, actionHost.childrenRect.height)

    MichiResponsive { id: responsive; availableWidth: root.width }

    Column {
        id: titleColumn
        anchors.left: parent.left
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
}
