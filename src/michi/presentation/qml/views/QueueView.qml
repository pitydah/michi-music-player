import QtQuick
import QtQuick.Layouts
import "../theme"
import "../components"

ColumnLayout {
    spacing: MichiTheme.space8

    Text {
        text: "Queue"
        font.pixelSize: MichiTheme.fontSizeTitle
        font.weight: MichiTheme.fontWeightBold
        color: MichiTheme.textPrimary
    }

    RowLayout {
        spacing: MichiTheme.space12

        Text {
            text: "Repeat:"
            font.pixelSize: MichiTheme.fontSizeBody
            color: MichiTheme.textSecondary
        }

        Text {
            text: "None"
            font.pixelSize: MichiTheme.fontSizeBody
            font.weight: queue.repeatMode === "NONE" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: queue.repeatMode === "NONE" ? MichiTheme.warning : MichiTheme.textSecondary

            MouseArea {
                anchors.fill: parent
                onClicked: queue.set_repeat_mode("NONE")
            }
        }

        Text {
            text: "One"
            font.pixelSize: MichiTheme.fontSizeBody
            font.weight: queue.repeatMode === "ONE" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: queue.repeatMode === "ONE" ? MichiTheme.warning : MichiTheme.textSecondary

            MouseArea {
                anchors.fill: parent
                onClicked: queue.set_repeat_mode("ONE")
            }
        }

        Text {
            text: "All"
            font.pixelSize: MichiTheme.fontSizeBody
            font.weight: queue.repeatMode === "ALL" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: queue.repeatMode === "ALL" ? MichiTheme.warning : MichiTheme.textSecondary

            MouseArea {
                anchors.fill: parent
                onClicked: queue.set_repeat_mode("ALL")
            }
        }

        Text {
            text: "Shuffle"
            font.pixelSize: MichiTheme.fontSizeBody
            font.weight: queue.shuffleEnabled ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: queue.shuffleEnabled ? MichiTheme.warning : MichiTheme.textSecondary

            MouseArea {
                anchors.fill: parent
                onClicked: queue.set_shuffle_enabled(!queue.shuffleEnabled)
            }
        }
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
