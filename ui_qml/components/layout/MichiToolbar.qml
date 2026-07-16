import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../foundations"

FocusScope {
    id: root

    property string title: ""
    property alias searchContent: searchHost.data
    property alias primaryActions: primaryHost.data
    property alias secondaryActions: secondaryHost.data
    property alias overflowContent: overflowHost.data
    property bool compactMode: responsive.compact

    implicitHeight: compactMode ? childrenColumn.implicitHeight : MichiTheme.toolbarHeight
    activeFocusOnTab: true

    Accessible.role: Accessible.ToolBar
    Accessible.name: title !== "" ? title : "Barra de herramientas"

    MichiResponsive { id: responsive; availableWidth: root.width }

    Keys.onRightPressed: function(event) {
        root.nextItemInFocusChain(true).forceActiveFocus()
        event.accepted = true
    }
    Keys.onLeftPressed: function(event) {
        root.nextItemInFocusChain(false).forceActiveFocus()
        event.accepted = true
    }

    Column {
        id: childrenColumn
        width: parent.width
        spacing: MichiTheme.spacing.sm

        RowLayout {
            width: parent.width
            height: MichiTheme.toolbarHeight
            spacing: MichiTheme.spacing.sm

            Text {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                visible: text !== ""
            }
            Item { id: searchHost; Layout.fillWidth: true; height: childrenRect.height }
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Toolbar"
    objectName: "michiToolbar"
    focus: true
            Row { id: secondaryHost; spacing: MichiTheme.spacing.xs; visible: !root.compactMode }
            Row { id: primaryHost; spacing: MichiTheme.spacing.xs }
            Row { id: overflowHost; spacing: MichiTheme.spacing.xs; visible: root.compactMode }
        }
    }
}
