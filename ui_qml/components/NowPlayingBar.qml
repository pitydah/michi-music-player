import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property var playbackState: (
        typeof nowplayingBridge !== "undefined" && nowplayingBridge
        ? nowplayingBridge
        : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    )

    height: MichiTheme.nowPlayingHeight

    Rectangle {
        anchors.fill: parent
        color: "#0F1219"

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: MichiTheme.borderWidth
            color: MichiTheme.colors.accentBlue
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width * 0.28
                height: parent.height
                spacing: MichiTheme.spacing.md

                NowPlayingCover {
                    anchors.verticalCenter: parent.verticalCenter
                    coverKey: root.playbackState ? root.playbackState.coverPath : ""
                }

                NowPlayingInfo {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - NowPlayingCover.width - MichiTheme.spacing.md
                    trackTitle: root.playbackState ? root.playbackState.trackTitle : "—"
                    trackArtist: root.playbackState ? root.playbackState.trackArtist : ""
                    trackAlbum: root.playbackState ? root.playbackState.trackAlbum : ""
                    isPlaying: root.playbackState ? root.playbackState.isPlaying : false
                }
            }

            Column {
                width: parent.width * 0.44
                height: parent.height
                spacing: 2

                NowPlayingControls {
                    anchors.horizontalCenter: parent.horizontalCenter
                    isPlaying: root.playbackState ? root.playbackState.isPlaying : false
                    shuffleEnabled: root.playbackState ? root.playbackState.shuffleEnabled : false
                    repeatMode: root.playbackState ? root.playbackState.repeatMode : "none"
                    onPlayClicked: { if (root.playbackState) root.playbackState.togglePlay() }
                    onPrevClicked: { if (root.playbackState) root.playbackState.previous() }
                    onNextClicked: { if (root.playbackState) root.playbackState.next() }
                    onShuffleClicked: { if (root.playbackState) root.playbackState.toggleShuffle() }
                    onRepeatClicked: { if (root.playbackState) root.playbackState.toggleRepeat() }
                }

                NowPlayingSeekBar {
                    anchors.horizontalCenter: parent.horizontalCenter
                    position: root.playbackState ? root.playbackState.position : 0
                    duration: root.playbackState ? root.playbackState.duration : 0
                    onSeekRequested: function(pos) {
                        if (root.playbackState) root.playbackState.seek(pos)
                    }
                }
            }

            Row {
                width: parent.width * 0.22
                height: parent.height
                layoutDirection: Qt.RightToLeft

                NowPlayingVolume {
                    anchors.verticalCenter: parent.verticalCenter
                    volume: root.playbackState ? root.playbackState.volume : 80
                    muted: root.playbackState ? root.playbackState.muted : false
                    onVolumeAdjusted: function(vol) {
                        if (root.playbackState) root.playbackState.setVolume(vol)
                    }
                    onMuteClicked: {
                        if (root.playbackState) root.playbackState.toggleMute()
                    }
                }
            }
        }
    }
}
