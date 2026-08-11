import QtQuick
import QtQuick.Layouts
import "../theme"
import "../components"

ColumnLayout {
    anchors.fill: parent
    spacing: MichiTheme.space8

    Text {
        text: "Queue"
        font.pixelSize: MichiTheme.fontSizeTitle
        font.weight: MichiTheme.fontWeightBold
        color: MichiTheme.textPrimary
    }

    QueuePanel {
        Layout.fillWidth: true
        Layout.fillHeight: true
        trackNames: queue.trackNames
        currentIndex: queue.currentIndex
        count: queue.count
        hasPrev: queue.hasPrevious
        hasNext: queue.hasNext
        onTrackClicked: idx => queue.play_index(idx)
        onClearClicked: queue.clear_queue()
        onPreviousRequested: queue.previous_track()
        onNextRequested: queue.next_track()
    }
}
