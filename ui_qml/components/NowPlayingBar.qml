import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property var ps: typeof nowplayingBridge !== "undefined" && nowplayingBridge
                     ? nowplayingBridge
                     : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _backendAvailable: root.ps ? root.ps.backendAvailable : false
    property string _emptyLabel: "Sin reproducción"

    height: MichiTheme.nowPlayingHeight
    visible: true
    z: 10

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceNowPlaying
        Rectangle {
            anchors.top: parent.top
            width: parent.width; height: 1
            color: MichiTheme.colors.surfaceNowPlayingBorder
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            // Cover + title
            Row {
                width: parent.width * 0.22; height: parent.height
                spacing: MichiTheme.spacing.md

                NowPlayingCover {
                    id: coverArt
                    anchors.verticalCenter: parent.verticalCenter
                    coverKey: root.ps ? root.ps.coverPath : ""
                    placeholderMode: !root._hasTrack
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3
                    width: Math.max(80, parent.width - coverArt.width - MichiTheme.spacing.md)
                    Text {
                        text: root._hasTrack && root.ps ? root.ps.trackTitle : root._emptyLabel
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: root._hasTrack ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                        elide: Text.ElideRight; width: parent.width
                    }
                    Text {
                        text: root._hasTrack && root.ps && root.ps.trackArtist
                              ? root.ps.trackArtist + (root.ps.trackAlbum ? " · " + root.ps.trackAlbum : "")
                              : "Selecciona una canción desde Biblioteca"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; width: parent.width
                    }
                }
            }

            // Controls + seek
            Column {
                width: parent.width * 0.45; height: parent.height; spacing: 2
                anchors.verticalCenter: parent.verticalCenter

                NowPlayingControls {
                    anchors.horizontalCenter: parent.horizontalCenter
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    enabled: true
                    opacity: 1.0
                    onPlayClicked: { if (root.ps) root.ps.togglePlay() }
                    onPrevClicked: { if (root.ps) root.ps.previous() }
                    onNextClicked: { if (root.ps) root.ps.next() }
                    onShuffleClicked: { if (root.ps) root.ps.toggleShuffle() }
                    onRepeatClicked: { if (root.ps) root.ps.toggleRepeat() }
                }

                NowPlayingSeekBar {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    enabled: root.ps ? root.ps.duration > 0 : false
                    opacity: 1.0
                    onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                }
            }

            // Volume
            Row {
                width: parent.width * 0.22; height: parent.height
                layoutDirection: Qt.RightToLeft; spacing: MichiTheme.spacing.sm

                NowPlayingVolume {
                    anchors.verticalCenter: parent.verticalCenter
                    volume: root.ps ? root.ps.volume : 80
                    muted: root.ps ? root.ps.muted : false
                    enabled: true; opacity: 1.0
                    onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                    onMuteClicked: { if (root.ps) root.ps.toggleMute() }
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            z: 5
            onClicked: {
                if (root._hasTrack && typeof navigationBridge !== "undefined")
                    navigationBridge.navigate("playback")
            }
        }
    }
}
