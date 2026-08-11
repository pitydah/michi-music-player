import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"

ColumnLayout {
    anchors.fill: parent
    spacing: 8

    Text {
        text: "Queue"
        font.pixelSize: 20; font.bold: true; color: "#e0e0e0"
    }

    QueuePanel {
        Layout.fillWidth: true
        Layout.fillHeight: true
        trackNames: queue.trackNames
        currentIndex: queue.currentIndex
        count: queue.count
        onTrackClicked: idx => queue.play_index(idx)
        onClearClicked: queue.clear_queue()
    }
}
