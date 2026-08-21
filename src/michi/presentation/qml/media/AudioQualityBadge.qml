import QtQuick
import "../primitives"
import "../theme"

Rectangle {
    id: root
    property string label: ""
    implicitWidth: qualityText.implicitWidth + MichiSpacing.md * 2
    implicitHeight: 24
    radius: MichiRadius.pill
    color: MichiSemanticColors.auroraCyanSurface
    border.width: 1
    border.color: MichiSemanticColors.auroraCyanBorder
    visible: label.length > 0
    MichiText {
        id: qualityText
        anchors.centerIn: parent
        text: root.label
        role: "technical"
        technical: true
        color: MichiPalette.auroraCyan
    }
}
