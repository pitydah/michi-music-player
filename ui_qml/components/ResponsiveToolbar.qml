import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
=======
import QtQuick.Controls as QQC2
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import QtQuick.Layouts
import "../theme"
import "foundations"

FocusScope {
    id: root

    property string title: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property alias searchContent: searchHost.data
    property alias primaryActions: primaryHost.data
    property alias secondaryActions: secondaryHost.data
    property alias overflowContent: overflowHost.data
    property int overflowThreshold: 600
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property var primaryActions: []
    property var secondaryActions: []
    property int overflowBreakpoint: MichiTheme.breakpointCompact
    property int visiblePrimaryCount: 0
    property string objectName: "responsiveToolbar"
>>>>>>> Stashed changes

    objectName: "ResponsiveToolbar"

    Accessible.role: Accessible.ToolBar
<<<<<<< Updated upstream
=======
    Accessible.name: root.title !== "" ? root.title : "Barra de herramientas"
=======
    property alias searchContent: searchHost.data
    property alias primaryActions: primaryHost.data
    property alias secondaryActions: secondaryHost.data
    property alias overflowContent: overflowHost.data
    property int overflowThreshold: 600

    objectName: "ResponsiveToolbar"

    Accessible.role: Accessible.ToolBar
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    Accessible.name: title !== "" ? title : "Barra de herramientas"

    implicitHeight: root.compactMode ? childrenColumn.implicitHeight : MichiTheme.toolbarHeight
    activeFocusOnTab: true

    readonly property bool compactMode: root.width < root.overflowThreshold
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    Keys.onRightPressed: function(event) {
        root.nextItemInFocusChain(true).forceActiveFocus()
        event.accepted = true
    }
    Keys.onLeftPressed: function(event) {
        root.nextItemInFocusChain(false).forceActiveFocus()
        event.accepted = true
    }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    Column {
        id: childrenColumn
        width: parent.width
        spacing: MichiTheme.spacing.sm

        RowLayout {
            width: parent.width
            height: MichiTheme.toolbarHeight
            spacing: MichiTheme.spacing.sm
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    Rectangle {
        anchors.fill: parent
        color: "transparent"

        RowLayout {
            id: contentRow
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.xs
=======
    Column {
        id: childrenColumn
        width: parent.width
        spacing: MichiTheme.spacing.sm

        RowLayout {
            width: parent.width
            height: MichiTheme.toolbarHeight
            spacing: MichiTheme.spacing.sm
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

            Text {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                visible: text !== ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            }

            Item {
                id: searchHost
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
            MichiIconButton {
                id: overflowButton
                iconText: "\u22EF"
                tooltipText: "Más acciones"
                visible: (root.compactMode && root.primaryActions.length > 0) || root.secondaryActions.length > 0
                onClicked: overflowMenu.popup()
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            Row {
                id: overflowHost
                spacing: MichiTheme.spacing.xs
                Layout.alignment: Qt.AlignVCenter
                visible: root.compactMode
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }
        }
    }
}
