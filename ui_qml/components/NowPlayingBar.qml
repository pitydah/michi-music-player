import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property QtObject playbackBridge: typeof playbackBridge !== "undefined" ? playbackBridge : null

    height: 64

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.03, 0.05, 0.95)

        Rectangle {
            anchors.top: parent.top
            width: parent.width; height: 1
            color: Qt.rgba(1.0, 1.0, 1.0, 0.04)
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.md
            anchors.rightMargin: MichiSpacing.md
            spacing: MichiSpacing.md

            Row {
                width: parent.width * 0.28
                height: parent.height
                spacing: MichiSpacing.md

                NowPlayingCover {
                    anchors.verticalCenter: parent.verticalCenter
                    coverKey: root.playbackBridge ? root.playbackBridge.coverPath : ""
                }

                NowPlayingInfo {
                    anchors.verticalCenter: parent.verticalCenter
                    trackTitle: root.playbackBridge ? root.playbackBridge.trackTitle : "—"
                    trackArtist: root.playbackBridge ? root.playbackBridge.trackArtist : ""
                    trackAlbum: root.playbackBridge ? root.playbackBridge.trackAlbum : ""
                    isPlaying: root.playbackBridge ? root.playbackBridge.isPlaying : false
                }
            }

            Column {
                width: parent.width * 0.44
                height: parent.height
                spacing: 2

                NowPlayingControls {
                    anchors.horizontalCenter: parent.horizontalCenter
                    isPlaying: root.playbackBridge ? root.playbackBridge.isPlaying : false
                    shuffleEnabled: root.playbackBridge ? root.playbackBridge.shuffleEnabled : false
                    repeatMode: root.playbackBridge ? root.playbackBridge.repeatMode : "none"
                    onPlayClicked: { if (root.playbackBridge) root.playbackBridge.togglePlay() }
                    onPrevClicked: { if (root.playbackBridge) root.playbackBridge.previous() }
                    onNextClicked: { if (root.playbackBridge) root.playbackBridge.next() }
                    onShuffleClicked: { if (root.playbackBridge) root.playbackBridge.toggleShuffle() }
                    onRepeatClicked: { if (root.playbackBridge) root.playbackBridge.toggleRepeat() }
                }

                NowPlayingSeekBar {
                    anchors.horizontalCenter: parent.horizontalCenter
                    position: root.playbackBridge ? root.playbackBridge.position : 0
                    duration: root.playbackBridge ? root.playbackBridge.duration : 0
                    onSeekRequested: function(pos) {
                        if (root.playbackBridge) root.playbackBridge.seek(pos)
                    }
                }
            }

            Row {
                width: parent.width * 0.22
                height: parent.height
                layoutDirection: Qt.RightToLeft

                NowPlayingVolume {
                    anchors.verticalCenter: parent.verticalCenter
                    volume: root.playbackBridge ? root.playbackBridge.volume : 80
                    onVolumeAdjusted: function(vol) {
                        if (root.playbackBridge) root.playbackBridge.setVolume(vol)
                    }
                }
            }
        }
    }
}
