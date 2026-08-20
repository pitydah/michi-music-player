import QtQuick
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root
    objectName: "queueView"
    property bool revealed: false
    signal closeRequested()

    Rectangle {
        anchors.fill: parent
        color: MichiSemanticColors.scrim
        opacity: root.revealed ? 1 : 0
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.panel }
        }
        MouseArea { anchors.fill: parent; onClicked: root.closeRequested() }
    }

    RowLayout {
        anchors.fill: parent
        spacing: MichiSpacing.xl

        Item { Layout.fillWidth: true }

        Item {
            Layout.fillHeight: true
            Layout.preferredWidth: Math.min(560, root.width)
            QueuePanel {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width
                x: root.revealed ? 0 : 36
                opacity: root.revealed ? 1 : 0
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
                onCloseRequested: root.closeRequested()
                Behavior on x {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.panel; easing.type: MichiMotion.outQuart }
                }
                Behavior on opacity {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.standard }
                }
            }
        }
    }
    Component.onCompleted: root.revealed = true
}
