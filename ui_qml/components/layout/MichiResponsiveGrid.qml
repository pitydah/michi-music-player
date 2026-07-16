import QtQuick
import "../../theme"
import "../foundations"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Responsive Grid"
    objectName: "michiResponsiveGrid"
    focus: true
    id: root

    property int requestedColumns: 0
    property int rowSpacing: MichiTheme.spacing.md
    property int columnSpacing: MichiTheme.spacing.md
    default property alias content: flow.data
    readonly property int columnCount: requestedColumns > 0 ? requestedColumns : responsive.columnCount
    readonly property real cellWidth: Math.max(1, (width - columnSpacing * (columnCount - 1)) / columnCount)

    implicitHeight: flow.implicitHeight

    function applyCellWidths() {
        for (var i = 0; i < flow.children.length; ++i)
            flow.children[i].width = root.cellWidth
    }

    onCellWidthChanged: applyCellWidths()
    Component.onCompleted: applyCellWidths()

    MichiResponsive { id: responsive; availableWidth: root.width }
    Flow {
        id: flow
        width: parent.width
        spacing: root.columnSpacing
        onChildrenChanged: root.applyCellWidths()
    }
}
