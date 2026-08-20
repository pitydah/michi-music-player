import QtQuick
import QtQuick.Layouts
import "../theme"
import "../controls"
import "../primitives"

RowLayout {
    id: root
    spacing: 6

    property alias volume: volSlider.value
    property alias muted: muteBtn.checked

    signal volumeChangeRequested(int value)
    signal muteToggleRequested(bool muted)

    MichiText {
        text: "Vol"
        role: "technical"
        technical: true
    }

    MichiSlider {
        id: volSlider
        from: 0; to: 100
        Layout.preferredWidth: 90
        accessibleName: "Volume"
        onMoved: root.volumeChangeRequested(value)
    }

    MichiIconButton {
        id: muteBtn
        iconName: checked ? "mute" : "volume"
        accessibleName: checked ? "Unmute" : "Mute"
        checkable: true
        onClicked: root.muteToggleRequested(checked)
    }
}
