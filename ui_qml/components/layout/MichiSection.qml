import QtQuick
import "../../theme"

Column {
    id: root

    property string title: ""
    property string subtitle: ""
    property alias actions: actionHost.data
    default property alias content: contentHost.data

    width: parent ? parent.width : implicitWidth
    spacing: MichiTheme.spacing.md

    Item {
        width: parent.width
        height: Math.max(titleColumn.implicitHeight, actionHost.implicitHeight)

        Column {
            id: titleColumn
            anchors.left: parent.left
            anchors.right: actionHost.left
            spacing: MichiTheme.spacing.xs
            Text {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }
            Text {
                text: root.subtitle
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.captionSize
                visible: text !== ""
            }
        }
        Row { id: actionHost; anchors.right: parent.right; spacing: MichiTheme.spacing.xs }
    }

    Column { id: contentHost; width: parent.width; spacing: MichiTheme.spacing.md }
}
