import QtQuick
import "../../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Michi Focus Ring")
    objectName: "michiFocusRing"
    id: root

    property Item control: null
    property real controlRadius: MichiTheme.radius.sm
    property bool keyboardFocusVisible: control ? control.activeFocus : false

    anchors.fill: control
    anchors.margins: -MichiTheme.focusOffset
    visible: keyboardFocusVisible
    z: 100

    Rectangle {
        anchors.fill: parent
        anchors.margins: -2
        radius: root.controlRadius + MichiTheme.focusOffset + 2
        color: "transparent"
        border.width: 2
        border.color: MichiTheme.colors.focusHalo
    }

    Rectangle {
        anchors.fill: parent
        radius: root.controlRadius + MichiTheme.focusOffset
        color: "transparent"
        border.width: MichiTheme.focusWidth
        border.color: MichiTheme.colors.borderFocus
    }
}
