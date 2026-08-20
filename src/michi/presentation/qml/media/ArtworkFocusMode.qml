import QtQuick
import QtQuick.Layouts
import "../components"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    spacing: MichiSpacing.lg

    Item { Layout.fillHeight: true }

    Artwork {
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: Math.min(360, Math.max(220, root.width * .42))
        Layout.preferredHeight: Layout.preferredWidth
        sourcePath: playback.artworkPath
        fallbackText: playback.title
        requestedSize: Math.round(width * Screen.devicePixelRatio)
    }

    ColumnLayout {
        Layout.alignment: Qt.AlignHCenter
        Layout.maximumWidth: 560
        spacing: MichiSpacing.xs
        MichiText {
            Layout.fillWidth: true
            text: playback.title || "Nothing playing"
            role: "title"
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            text: [playback.artist, playback.album].filter(value => value !== "").join(" · ")
            role: "secondary"
            horizontalAlignment: Text.AlignHCenter
            visible: text.length > 0
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            text: playback.qualityLabel
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignHCenter
            visible: text.length > 0
        }
    }

    PlaybackProgress {
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: Math.min(620, root.width * .76)
        position: playback.position
        duration: Math.max(playback.duration, 1)
        seekEnabled: playback.duration > 0
        onSeekRequested: seconds => playback.seek_seconds(seconds)
    }

    PlaybackControls {
        Layout.alignment: Qt.AlignHCenter
        playing: playback.status === "playing"
        canPlay: playback.fileName !== ""
        canPause: playback.status === "playing"
        canStop: playback.status !== "stopped"
        canPrev: queue.hasPrevious
        canNext: queue.hasNext
        onPlayClicked: playback.play()
        onPauseClicked: playback.pause()
        onStopClicked: playback.stop()
        onPrevClicked: queue.previous_track()
        onNextClicked: queue.next_track()
    }

    Item { Layout.fillHeight: true }
}
