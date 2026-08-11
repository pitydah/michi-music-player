import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"

ColumnLayout {
    anchors.fill: parent
    spacing: 12

    Text {
        Layout.alignment: Qt.AlignHCenter
        text: "Now Playing"
        font.pixelSize: 20; font.bold: true; color: "#e0e0e0"
    }

    NowPlayingPanel {
        Layout.fillWidth: true
        fileName: playback.fileName
        position: playback.position
        duration: Math.max(playback.duration, 1)
        statusText: playback.status
        statusColor: playback.status === "playing" ? "#66cc88" :
                     playback.status === "paused" ? "#ccaa44" : "#8888aa"
        seekEnabled: playback.duration > 0
        onSeekRequested: secs => playback.seek_seconds(secs)
    }

    PlaybackControls {
        Layout.alignment: Qt.AlignHCenter
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

    VolumeControl {
        Layout.alignment: Qt.AlignHCenter
        volume: playback.volume
        muted: playback.muted
        onVolumeChangeRequested: v => playback.set_volume(v)
        onMuteToggleRequested: m => playback.set_muted(m)
    }

    Item { Layout.fillHeight: true }
}
