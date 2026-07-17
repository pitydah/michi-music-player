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
    property int radius: MichiTheme.radius.sm

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiTheme.colors.surfaceInput
        border.color: {
            if (root.focused) return MichiTheme.colors.borderFocus
            if (root.hoveredInput) return MichiTheme.colors.borderCard
            return MichiTheme.colors.borderSubtle
        }
        border.width: root.focused ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
    }
}
