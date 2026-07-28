import QtQuick

MichiBaseSurface {
    Accessible.role: Accessible.Pane
    Accessible.name: "Input Material"
    objectName: "inputMaterial"
    focus: true
    id: root

    property bool focused: false
    property bool hoveredInput: false
    radius: MichiTheme.radius.sm
    level: 3
    selected: root.focused
    hovered: root.hoveredInput
    borderVisible: true
}
