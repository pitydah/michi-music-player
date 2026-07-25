import QtQuick
import "../../theme"

Item {
    id: root
    objectName: "michiResponsiveGrid"

    property int minimumCellWidth: 260
    property int maximumColumns: 4
    property int compactColumns: 1
    property int spacing: MichiTheme.spacing.md
    property int requestedColumns: 0
    default property alias content: flow.data

    readonly property int calculatedColumns: Math.max(
        compactColumns,
        Math.min(maximumColumns,
                 Math.floor((width + spacing) / (minimumCellWidth + spacing))))
    readonly property int columnCount: requestedColumns > 0
                                       ? Math.min(maximumColumns, requestedColumns)
                                       : calculatedColumns
    readonly property real cellWidth: Math.max(
        1, (width - spacing * (columnCount - 1)) / columnCount)
    implicitHeight: flow.implicitHeight

    function applyCellWidths() {
        for (var index = 0; index < flow.children.length; ++index) {
            var child = flow.children[index]
            if (child)
                child.width = root.cellWidth
        }
    }

    onCellWidthChanged: applyCellWidths()
    Component.onCompleted: applyCellWidths()

    Flow {
        id: flow
        width: parent.width
        spacing: root.spacing
        onChildrenChanged: root.applyCellWidths()
    }
}
