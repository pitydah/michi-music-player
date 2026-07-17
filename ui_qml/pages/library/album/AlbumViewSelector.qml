import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

RowLayout {
    id: root

    property int currentView: 0
    signal viewChanged(int index)

    spacing: MichiTheme.spacing.xs

    Repeater {
        model: [
            {icon: "../../../../icons/view/warm_view_grid.svg", tooltip: "Vista cuadrícula"},
            {icon: "../../../../icons/view/warm_view_coverflow.svg", tooltip: "Cover Flow"},
            {icon: "../../../../icons/view/warm_view_vinyl.svg", tooltip: "Pared de vinilos"},
            {icon: "../../../../icons/view/warm_view_timeline.svg", tooltip: "Línea de tiempo"},
            {icon: "../../../../icons/view/warm_view_magazine.svg", tooltip: "Revista"},
        ]

        MichiIconButton {
            iconSource: modelData.icon
            tooltipText: modelData.tooltip
            btnSize: 28
            selected: currentView === index
            onClicked: {
                root.currentView = index
                root.viewChanged(index)
            }
        }
    }
}
