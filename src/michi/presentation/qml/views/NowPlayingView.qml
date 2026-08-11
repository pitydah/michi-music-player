import QtQuick
import QtQuick.Layouts
import "../theme"
import "../components"

ColumnLayout {
    spacing: MichiTheme.space12

    Text {
        Layout.alignment: Qt.AlignHCenter
        text: "Now Playing"
        font.pixelSize: MichiTheme.fontSizeTitle
        font.weight: MichiTheme.fontWeightBold
        color: MichiTheme.textPrimary
    }

    NowPlayingPanel {
        Layout.fillWidth: true
        fileName: playback.fileName
        position: playback.position
        duration: Math.max(playback.duration, 1)
        statusText: playback.status
        statusColor: playback.status === "playing" ? MichiTheme.success :
                     playback.status === "paused" ? MichiTheme.warning : MichiTheme.textMuted
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
