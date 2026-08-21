import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

RowLayout {
    id: root
    property int position: 0
    property int duration: 1
    property bool seekEnabled: true
    signal seekRequested(int seconds)
    spacing: MichiSpacing.sm

    function formatTime(seconds) {
        if (seconds <= 0) return "0:00"
        var minutes = Math.floor(seconds / 60)
        var remainder = Math.floor(seconds % 60)
        return minutes + ":" + (remainder < 10 ? "0" : "") + remainder
    }

    MichiText { text: root.formatTime(root.position); role: "technical"; technical: true; Layout.preferredWidth: 38 }
    MichiSlider {
        Layout.fillWidth: true
        from: 0; to: Math.max(root.duration, 1); value: root.position
        enabled: root.seekEnabled
        accessibleName: "Playback position"
        onMoved: root.seekRequested(value)
    }
    MichiText { text: root.formatTime(root.duration); role: "technical"; technical: true; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 38 }
}
