import QtQuick
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root
    objectName: "queueView"

    RowLayout {
        anchors.fill: parent
        spacing: MichiSpacing.xl

        Item { Layout.fillWidth: true }

        QueuePanel {
            Layout.fillHeight: true
            Layout.preferredWidth: Math.min(560, root.width)
            trackRows: queue.trackRows
            currentIndex: queue.currentIndex
            count: queue.count
            hasPrev: queue.hasPrevious
            hasNext: queue.hasNext
            repeatMode: queue.repeatMode
            shuffleEnabled: queue.shuffleEnabled
            onTrackClicked: index => queue.play_index(index)
            onMoveRequested: (fromIndex, toIndex) => queue.move_track(fromIndex, toIndex)
            onRemoveRequested: index => queue.remove_track(index)
            onClearClicked: queue.clear_queue()
            onPreviousRequested: queue.previous_track()
            onNextRequested: queue.next_track()
            onRepeatModeRequested: mode => queue.set_repeat_mode(mode)
            onShuffleRequested: enabled => queue.set_shuffle_enabled(enabled)
        }
    }
}
