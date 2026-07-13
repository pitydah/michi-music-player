import QtQuick
import "../../theme"

Rectangle {
    id: root

    property Item control: null
    property real controlRadius: MichiTheme.radiusSm
    property bool keyboardFocusVisible: control ? control.activeFocus : false

    anchors.fill: control
    anchors.margins: -MichiTheme.focusOffset
    radius: controlRadius + MichiTheme.focusOffset
    color: "transparent"
    border.width: MichiTheme.focusWidth
    border.color: MichiTheme.colors.borderFocus
    visible: keyboardFocusVisible
    z: 100
}
