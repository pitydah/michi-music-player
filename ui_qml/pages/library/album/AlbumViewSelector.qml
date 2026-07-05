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
            {label: "Grid", icon: "⊞"},
            {label: "Cover", icon: "⊡"},
            {label: "Vinyl", icon: "◉"},
            {label: "Years", icon: "⊟"},
            {label: "Mag", icon: "▣"},
        ]

        MichiButton {
            text: modelData.label
            variant: currentView === index ? "primary" : "ghost"
            implicitHeight: 28
            onClicked: {
                root.currentView = index
                root.viewChanged(index)
            }
        }
    }
}
