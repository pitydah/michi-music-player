import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "qml/components"

ApplicationWindow {
    id: window
    visible: true
    width: 1100
    height: 700
    minimumWidth: 800
    minimumHeight: 480
    title: "Michi Music Player"
    color: "#1a1a2e"

    Shortcut { sequence: "Space"; onActivated: playback.status === "playing" ? playback.pause() : playback.play() }
    Shortcut { sequence: "Left"; onActivated: queue.previous_track() }
    Shortcut { sequence: "Right"; onActivated: queue.next_track() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: window.close() }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        ColumnLayout {
            Layout.preferredWidth: 400
            Layout.fillHeight: true
            spacing: 12

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Michi Music Player"
                font.pixelSize: 22; font.bold: true; color: "#e0e0e0"
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

        LibraryPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentDir: library.currentDir
            fileList: library.files
            fileCount: library.fileCount
            onScanRequested: dir => library.scan(dir)
            onSearchRequested: q => library.search(q)
            onTrackActivated: idx => library.activate(idx)
        }
    }
}
