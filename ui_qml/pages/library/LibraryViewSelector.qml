import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

RowLayout {
    id: root

    property int currentView: 0

    signal viewChanged(int index)

    spacing: MichiTheme.spacing.xs

    Repeater {
        model: [
            {icon: "view-list", tooltip: "Lista"},
            {icon: "view-grid", tooltip: "Cuadrícula"},
            {icon: "view-coverflow", tooltip: "CoverFlow"},
            {icon: "view-details", tooltip: "Detalles"},
            {icon: "view-tree", tooltip: "Árbol"}
        ]
        Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library View Selector"
    objectName: "libraryViewSelector"
    focus: true
            width: 28; height: 28; radius: MichiTheme.radiusXs
            color: root.currentView === index ? MichiTheme.colors.accentSurface : "transparent"
            border.color: root.currentView === index ? MichiTheme.colors.accentBlue : "transparent"

            Text {
                anchors.centerIn: parent
                text: modelData.icon.substring(5, 6).toUpperCase()
                color: root.currentView === index ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                font.pixelSize: 12
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: { root.currentView = index; root.viewChanged(index) }
            }
        }
    }
}
