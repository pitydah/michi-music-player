import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "foundations"

FocusScope {
    id: root

    property string title: ""
    property var primaryActions: []
    property var secondaryActions: []
    property int overflowBreakpoint: MichiTheme.breakpointCompact
    property int visiblePrimaryCount: 0
    property string objectName: "responsiveToolbar"

    readonly property bool compactMode: root.width < root.overflowBreakpoint

    implicitHeight: Math.max(MichiTheme.toolbarHeight, contentRow.implicitHeight + MichiTheme.spacing.sm * 2)
    activeFocusOnTab: true

    Accessible.role: Accessible.ToolBar
    Accessible.name: root.title !== "" ? root.title : "Barra de herramientas"

    Keys.onRightPressed: function(event) {
        root.nextItemInFocusChain(true).forceActiveFocus()
        event.accepted = true
    }
    Keys.onLeftPressed: function(event) {
        root.nextItemInFocusChain(false).forceActiveFocus()
        event.accepted = true
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        RowLayout {
            id: contentRow
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.xs

            Text {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                visible: text !== ""
                Layout.fillWidth: true
            }

            Repeater {
                model: {
                    if (root.compactMode) return []
                    return root.primaryActions.slice(0, root.visiblePrimaryCount > 0 ? root.visiblePrimaryCount : root.primaryActions.length)
                }
                delegate: MichiButton {
                    text: modelData.text || ""
                    variant: modelData.variant || "ghost"
                    iconSource: modelData.iconSource || ""
                    onClicked: modelData.action ? modelData.action() : undefined
                    objectName: root.objectName + "/action/" + (modelData.text || index)
                }
            }

            Menu {
                id: overflowMenu
                title: "Más acciones"
                objectName: root.objectName + "/overflowMenu"

                Instantiator {
                    model: root.compactMode ? root.primaryActions : root.secondaryActions
                    MenuItem {
                        text: modelData.text || ""
                        onTriggered: modelData.action ? modelData.action() : undefined
                        objectName: root.objectName + "/menuItem/" + (modelData.text || index)
                    }
                    onObjectAdded: function(index, object) { overflowMenu.insertItem(index, object) }
                    onObjectRemoved: function(index, object) { overflowMenu.removeItem(object) }
                }
            }

            MichiIconButton {
                id: overflowButton
                iconText: "\u22EF"
                tooltipText: "Más acciones"
                visible: (root.compactMode && root.primaryActions.length > 0) || root.secondaryActions.length > 0
                onClicked: overflowMenu.popup()
            }
        }
    }
}
