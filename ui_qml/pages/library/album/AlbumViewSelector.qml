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
            {icon: "../../../../icons/view/library-grid.svg", tooltip: qsTr("Vista cuadrícula")},
            {icon: "../../../../icons/view/library-coverflow.svg", tooltip: qsTr("Cover Flow")},
            {icon: "../../../../icons/view/library-vinyl.svg", tooltip: qsTr("Pared de vinilos")},
            {icon: "../../../../icons/view/library-timeline.svg", tooltip: qsTr("Línea de tiempo")},
            {icon: "../../../../icons/view/library-editorial.svg", tooltip: qsTr("Revista")},
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
