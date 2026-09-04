import QtQuick
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
    // LIB-A §13: right-click sobre la CELL (contexto de la columna exacta)
    // — nunca dispara sort. El sort queda para left-click.
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
    // LIB-A §13: right-click abre el contexto de la COLUMNA (sort explícito
    // asc/desc, hide excepto title, reset width) — independiente del click
    // izquierdo de sort y del drag/handle de resize.
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

        Rectangle {
            visible: root.resizable
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            width: 1
            height: MichiSpacing.lg
            color: resizeArea.containsMouse || resizeArea.pressed
                ? MichiSemanticColors.auroraCyanBorder
                : MichiSemanticColors.borderSubtle
        }
    }
}
