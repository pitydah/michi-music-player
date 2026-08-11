import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

RowLayout {
    id: root
    spacing: 6

    property alias volume: volSlider.value
    property alias muted: muteBtn.checked

    signal volumeChangeRequested(int value)
    signal muteToggleRequested(bool muted)

    Text {
        text: "Vol"
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.textSecondary
    }

    MichiSlider {
        id: volSlider
        from: 0; to: 100
        Layout.preferredWidth: 90
        onMoved: root.volumeChangeRequested(value)
    }

    MichiButton {
        id: muteBtn
        text: checked ? "🔇" : "🔊"
        variant: "ghost"
        checkable: true
        onClicked: root.muteToggleRequested(checked)
    }
}
