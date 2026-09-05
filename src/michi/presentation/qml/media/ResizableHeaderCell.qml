import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root

    property string label: ""
    property string columnKey: ""
    property real columnWidth: 100
    property real resizeBaseWidth: columnWidth
    property bool resizable: true
    property bool sortable: false
    property bool sortActive: false
    property bool sortDescending: false
    signal sortRequested(string columnKey)
    signal resizeRequested(string columnKey, real width)
    signal resetRequested(string columnKey)
    signal contextRequested(string columnKey)

    implicitWidth: columnWidth
    implicitHeight: MichiMetrics.controlMedium

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.xs
        anchors.rightMargin: 8
        spacing: MichiSpacing.xs

        MichiText {
            Layout.fillWidth: true
            text: root.label
            role: "technical"
            technical: true
            color: root.sortActive ? MichiPalette.auroraCyan
                : cellHover.hovered ? MichiPalette.textPrimary
                : MichiPalette.textMuted
            elide: Text.ElideRight
        }
        MichiIcon {
            visible: root.sortActive
            Layout.preferredWidth: 12
            Layout.preferredHeight: 12
            name: root.sortDescending ? "sort-descending" : "sort-ascending"
            iconColor: MichiPalette.auroraCyan
        }
    }

    HoverHandler {
        id: cellHover
        enabled: root.sortable
        cursorShape: root.sortable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: root.sortable
        onTapped: {
            MichiAccessibility.notePointer()
            root.sortRequested(root.columnKey)
        }
    }
    TapHandler {
        acceptedButtons: Qt.RightButton
        enabled: root.columnKey.length > 0
        onTapped: {
            MichiAccessibility.notePointer()
            root.contextRequested(root.columnKey)
        }
    }

    MouseArea {
        id: resizeArea
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        width: 8
        z: 2
        hoverEnabled: true
        cursorShape: Qt.SplitHCursor
        acceptedButtons: Qt.LeftButton
        enabled: root.resizable
        property real pressGlobalX: 0
        property real pressWidth: 0

        onPressed: mouse => {
            pressGlobalX = mapToGlobal(mouse.x, mouse.y).x
            pressWidth = root.resizeBaseWidth
            mouse.accepted = true
        }
        onPositionChanged: mouse => {
            if (!pressed)
                return
            var globalX = mapToGlobal(mouse.x, mouse.y).x
            root.resizeRequested(root.columnKey,
                pressWidth + globalX - pressGlobalX)
        }
        onDoubleClicked: mouse => {
            root.resetRequested(root.columnKey)
            mouse.accepted = true
        }

        // During drag, explain the operation rather than showing a heavy
        // full-table guide.  This stays local to the column boundary and
        // reflects the canonical clamped width in real time.
        ToolTip.visible: pressed
        ToolTip.delay: 0
        ToolTip.text: qsTr("%1 · %2 px")
            .arg(root.label.length > 0 ? root.label : root.columnKey)
            .arg(Math.round(root.columnWidth))

        Rectangle {
            visible: root.resizable
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            width: 1
            height: 14
            color: resizeArea.containsMouse || resizeArea.pressed
                ? MichiSemanticColors.auroraCyanBorder
                : MichiSemanticColors.borderSubtle
            opacity: resizeArea.containsMouse || resizeArea.pressed ? 1 : 0.34

            Behavior on opacity {
                enabled: !MichiAccessibility.reducedMotion
                NumberAnimation { duration: MichiMotion.micro }
            }
        }
    }
}
