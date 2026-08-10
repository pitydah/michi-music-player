import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

RowLayout {
    id: root
    spacing: 6

    property alias volume: volSlider.value
    property alias muted: muteBtn.checked

    signal volumeChangeRequested(int value)
    signal muteToggleRequested(bool muted)

    Text {
        text: "Vol"
        font.pixelSize: 11
        color: "#8888aa"
    }

    Slider {
        id: volSlider
        from: 0; to: 100
        Layout.preferredWidth: 90
        onMoved: root.volumeChangeRequested(value)
    }

    Button {
        id: muteBtn
        text: checked ? "🔇" : "🔊"
        checkable: true
        flat: true
        onClicked: root.muteToggleRequested(checked)
    }
}
