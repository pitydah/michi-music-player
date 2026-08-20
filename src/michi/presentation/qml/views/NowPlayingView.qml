import QtQuick
import QtQuick.Layouts
import "../theme"
import "../components"
import "../controls"
import "../media"
import "../patterns"

Item {
    id: root
    property bool focusMode: false

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.space12

        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Now Playing"
                font.pixelSize: MichiTheme.fontSizeTitle
                font.weight: MichiTheme.fontWeightBold
                color: MichiTheme.textPrimary
            }
            MichiButton {
                text: root.focusMode ? "Standard view" : "Focus mode"
                iconName: root.focusMode ? "library" : "artist"
                variant: "secondary"
                enabled: playback.fileName !== ""
                onClicked: root.focusMode = !root.focusMode
            }
        }

        ErrorState {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : 0
            visible: playback.errorMessage !== ""
            title: "Playback unavailable"
            message: playback.errorMessage
            actionText: ""
        }

        Loader {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: root.focusMode ? focusComponent : standardComponent
        }
    }

    Component {
        id: focusComponent
        ArtworkFocusMode { }
    }

    Component {
        id: standardComponent
        ColumnLayout {
            spacing: MichiTheme.space12

            NowPlayingPanel {
                Layout.fillWidth: true
                fileName: playback.title
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

            VolumeControl {
                Layout.alignment: Qt.AlignHCenter
                volume: playback.volume
                muted: playback.muted
                onVolumeChangeRequested: v => playback.set_volume(v)
                onMuteToggleRequested: m => playback.set_muted(m)
            }

            Item { Layout.fillHeight: true }
        }
    }
}
