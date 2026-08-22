import QtQuick
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root
    objectName: "queueView"
    property bool revealed: false
    property bool _closing: false
    signal closeRequested()
    focus: true

    // Animated dismissal: fade/slide out, then emit closeRequested so the
    // AppShell Loader destroys this view (instant teardown would pop).
    function dismiss() {
        if (root._closing)
            return
        root._closing = true
        root.revealed = false
        dismissTimer.start()
    }

    Keys.onEscapePressed: root.dismiss()

    Rectangle {
        anchors.fill: parent
        color: MichiSemanticColors.scrim
        opacity: root.revealed ? 1 : 0
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.panel }
        }
        MouseArea {
            anchors.fill: parent
            enabled: root.revealed
            onClicked: root.dismiss()
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: MichiSpacing.xl

        Item { Layout.fillWidth: true }

        Item {
            Layout.fillHeight: true
            Layout.preferredWidth: Math.max(360, Math.min(520, root.width * 0.46))
            Accessible.role: Accessible.Dialog
            Accessible.name: "Queue"

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
                onRemoveRequested: index => {
                    queue.remove_track(index)
                    window.showToast(qsTr("Removed from queue"))
                }
                onClearClicked: {
                    queue.clear_queue()
                    window.showToast(qsTr("Queue cleared"))
                }
                onPreviousRequested: queue.previous_track()
                onNextRequested: queue.next_track()
                onRepeatModeRequested: mode => queue.set_repeat_mode(mode)
                onShuffleRequested: enabled => queue.set_shuffle_enabled(enabled)
                onCloseRequested: root.dismiss()
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
    Timer {
        id: dismissTimer
        interval: MichiMotion.panel + 20
        onTriggered: root.closeRequested()
    }
    Component.onCompleted: {
        root.revealed = true
        root.forceActiveFocus()
    }
}
