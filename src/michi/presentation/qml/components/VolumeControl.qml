import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

RowLayout {
    id: root
    spacing: 6

    property alias volume: volSlider.value
    property alias muted: muteBtn.checked

    signal volumeChanged(int value)
    signal muteToggled(bool muted)

    Text {
        text: "Vol"
        font.pixelSize: 11
        color: "#8888aa"
    }

    Slider {
        id: volSlider
        from: 0; to: 100
        Layout.preferredWidth: 90
        onValueChanged: root.volumeChanged(value)
    }

    Button {
        id: muteBtn
        text: checked ? "🔇" : "🔊"
        checkable: true
        flat: true
        onClicked: root.muteToggled(checked)
    }
}
