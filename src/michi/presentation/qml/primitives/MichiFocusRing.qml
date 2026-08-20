import QtQuick
import "../theme"

Rectangle {
    id: root
    property bool visualFocus: false
    anchors.fill: parent
    anchors.margins: -2
    color: "transparent"
    property int ringRadius: MichiRadius.md + 2
    radius: ringRadius
    border.width: visualFocus ? (MichiAccessibility.highContrast ? 2 : 1) : 0
    border.color: MichiSemanticColors.focusRing
    opacity: visualFocus ? 1 : 0
    visible: opacity > 0
    Behavior on opacity {
        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
    }
}
