import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Input Material"
    objectName: "inputMaterial"
    focus: true
    id: root

    property bool focused: false
    property bool hoveredInput: false
    property int radius: MichiTheme.radiusSm

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiTheme.colors.surfaceInput
        border.color: {
            if (root.focused) return MichiTheme.colors.borderFocus
            if (root.hoveredInput) return Qt.rgba(1.0, 1.0, 1.0, 0.12)
            return MichiTheme.colors.borderSubtle
        }
        border.width: root.focused ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
    }
}
