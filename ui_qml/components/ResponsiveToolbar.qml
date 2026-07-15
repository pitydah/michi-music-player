import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Controls
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
    property var primaryActions: []
    property var secondaryActions: []
    property int overflowBreakpoint: MichiTheme.breakpointCompact
    property int visiblePrimaryCount: 0
    property string objectName: "responsiveToolbar"

    objectName: "ResponsiveToolbar"

    Accessible.role: Accessible.ToolBar
    Accessible.name: root.title !== "" ? root.title : "Barra de herramientas"
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
    Rectangle {
        anchors.fill: parent
        color: "transparent"

        RowLayout {
            id: contentRow
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.xs
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

            MichiIconButton {
                id: overflowButton
                iconText: "\u22EF"
                tooltipText: "Más acciones"
                visible: (root.compactMode && root.primaryActions.length > 0) || root.secondaryActions.length > 0
                onClicked: overflowMenu.popup()
            }

            Item {
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
