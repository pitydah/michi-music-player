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
    property bool _canPlay: root.ps ? root.ps.backendAvailable : false
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property string _emptyLabel: "Sin reproducción"

    height: MichiTheme.nowPlayingHeight
    visible: true
    z: 10

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceNowPlaying
        z: 10

        Rectangle {
            anchors.top: parent.top
            width: parent.width; height: 1
            color: MichiTheme.colors.surfaceNowPlayingBorder
            z: 11
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md
            z: 12

            Row {
                width: parent.width * 0.22; height: parent.height
                spacing: MichiTheme.spacing.md

                NowPlayingCover {
                    id: coverArt
                    anchors.verticalCenter: parent.verticalCenter
                    coverKey: root.ps ? root.ps.coverPath : ""
                    placeholderMode: !root._hasTrack
                    opacity: root._hasTrack ? 1.0 : 0.5
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3
                    width: Math.max(80, parent.width - coverArt.width - MichiTheme.spacing.md)

                    Text {
                        text: root._hasTrack && root.ps ? root.ps.trackTitle : root._emptyLabel
                        color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: root._hasTrack ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                        elide: Text.ElideRight
                        width: parent.width
                    }

                    Text {
                        text: root._hasTrack && root.ps && root.ps.trackArtist
                              ? root.ps.trackArtist + (root.ps.trackAlbum ? " · " + root.ps.trackAlbum : "")
                              : root._canPlay ? "Selecciona una canción desde Biblioteca" : "Playback no disponible"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }
            }

            Item {
                width: parent.width * 0.08; height: 1
            }

            Column {
                width: parent.width * 0.40; height: parent.height
                spacing: 2
                anchors.verticalCenter: parent.verticalCenter

                NowPlayingControls {
                    anchors.horizontalCenter: parent.horizontalCenter
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    enabled: root._canPlay && root._hasTrack
                    opacity: root._canPlay && root._hasTrack ? 1.0 : 0.45
                    onPlayClicked: {
                        if (!root._canPlay) { if (root.notif) root.notif.showMessage("Playback no disponible", "warning"); return }
                        if (root.ps) root.ps.togglePlay()
                    }
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
                    enabled: root._canPlay && root._hasTrack && (root.ps ? root.ps.duration > 0 : false)
                    opacity: root._canPlay && root._hasTrack && (root.ps ? root.ps.duration > 0 : false) ? 1.0 : 0.45
                    onSeekRequested: function(pos) {
                        if (!root._canPlay) { if (root.notif) root.notif.showMessage("Playback no disponible", "warning"); return }
                        if (root.ps) root.ps.seek(pos)
                    }
                }
            }

            Row {
                width: parent.width * 0.22; height: parent.height
                layoutDirection: Qt.RightToLeft
                spacing: MichiTheme.spacing.xs

                NowPlayingVolume {
                    anchors.verticalCenter: parent.verticalCenter
                    volume: root.ps ? root.ps.volume : 80
                    muted: root.ps ? root.ps.muted : false
                    enabled: root._canPlay && root._hasTrack
                    opacity: root._canPlay && root._hasTrack ? 1.0 : 0.45
                    onVolumeAdjusted: function(vol) {
                        if (!root._canPlay) { if (root.notif) root.notif.showMessage("Playback no disponible", "warning"); return }
                        if (root.ps) root.ps.setVolume(vol)
                    }
                    onMuteClicked: {
                        if (!root._canPlay) { if (root.notif) root.notif.showMessage("Playback no disponible", "warning"); return }
                        if (root.ps) root.ps.toggleMute()
                    }
                }

                MichiIconButton {
                    iconText: "⏏"
                    tooltipText: "Reproducción"
                    btnSize: 22
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: {
                        if (typeof navigationBridge !== "undefined") navigationBridge.navigate("playback")
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        z: 5
        cursorShape: root._canPlay && root._hasTrack ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root._canPlay && root._hasTrack && typeof navigationBridge !== "undefined")
                navigationBridge.navigate("playback")
        }
    }
}
