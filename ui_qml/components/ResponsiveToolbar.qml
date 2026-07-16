import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"
import "foundations"

FocusScope {
    id: root

    property string title: ""
    property alias searchContent: searchHost.data
    property alias primaryActions: primaryHost.data
    property alias secondaryActions: secondaryHost.data
    property alias overflowContent: overflowHost.data
    property int overflowThreshold: 600

    objectName: "ResponsiveToolbar"

    Accessible.role: Accessible.ToolBar
    Accessible.name: title !== "" ? title : "Barra de herramientas"

    implicitHeight: root.compactMode ? childrenColumn.implicitHeight : MichiTheme.toolbarHeight
    activeFocusOnTab: true

    readonly property bool compactMode: root.width < root.overflowThreshold

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

            Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Responsive Toolbar"
    objectName: "responsiveToolbar"
    focus: true
                id: searchHost
                Layout.fillWidth: true
                height: childrenRect.height
                Layout.alignment: Qt.AlignVCenter
            }

            Row {
                id: secondaryHost
                spacing: MichiTheme.spacing.xs
                Layout.alignment: Qt.AlignVCenter
                visible: !root.compactMode
            }

            Row {
                id: primaryHost
                spacing: MichiTheme.spacing.xs
                Layout.alignment: Qt.AlignVCenter
            }

            Row {
                id: overflowHost
                spacing: MichiTheme.spacing.xs
                Layout.alignment: Qt.AlignVCenter
                visible: root.compactMode
            }
        }
    }
}
