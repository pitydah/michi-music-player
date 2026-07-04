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

    height: MichiTheme.nowPlayingHeight
    visible: true

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceNowPlaying
        border.color: MichiTheme.colors.accentBlue
        border.width: 1

        Rectangle {
            anchors.top: parent.top
            width: 60; height: 2
            anchors.horizontalCenter: parent.horizontalCenter
            radius: 1; color: MichiTheme.colors.accentBlue; opacity: 0.5
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width * 0.28; height: parent.height
                spacing: MichiTheme.spacing.md

                NowPlayingCover {
                    anchors.verticalCenter: parent.verticalCenter
                    coverKey: root.ps ? root.ps.coverPath : ""
                }

                NowPlayingInfo {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - NowPlayingCover.width - MichiTheme.spacing.md
                    trackTitle: root.ps ? root.ps.trackTitle : "—"
                    trackArtist: root.ps ? root.ps.trackArtist : ""
                    trackAlbum: root.ps ? root.ps.trackAlbum : ""
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    backendAvailable: root.ps ? root.ps.backendAvailable : false
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    visible: root.ps && !root.ps.backendAvailable
                    StatusBadge { text: "Safe mode"; kind: "experimental" }
                    StatusBadge { text: root.ps && root.ps.playbackStatus === "unavailable" ? "No disponible" : root.ps && root.ps.errorMessage ? root.ps.errorMessage : ""; kind: "disconnected"; visible: text !== "" }
                }
            }

            Column {
                width: parent.width * 0.44; height: parent.height; spacing: 2

                NowPlayingControls {
                    anchors.horizontalCenter: parent.horizontalCenter
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    onPlayClicked: {
                        if (root.ps) root.ps.togglePlay()
                        if (root.notif && root.ps && !root.ps.backendAvailable) root.notif.showMessage("Playback no disponible", "warning")
                    }
                    onPrevClicked: { if (root.ps) root.ps.previous() }
                    onNextClicked: { if (root.ps) root.ps.next() }
                    onShuffleClicked: { if (root.ps) root.ps.toggleShuffle() }
                    onRepeatClicked: { if (root.ps) root.ps.toggleRepeat() }
                }

                NowPlayingSeekBar {
                    anchors.horizontalCenter: parent.horizontalCenter
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    onSeekRequested: function(pos) {
                        if (root.ps) {
                            if (root.ps.duration <= 0) {
                                if (root.notif) root.notif.showMessage("No se puede buscar", "warning")
                            } else {
                                root.ps.seek(pos)
                            }
                        }
                    }
                }
            }

            Row {
                width: parent.width * 0.22; height: parent.height
                layoutDirection: Qt.RightToLeft

                NowPlayingVolume {
                    anchors.verticalCenter: parent.verticalCenter
                    volume: root.ps ? root.ps.volume : 80
                    muted: root.ps ? root.ps.muted : false
                    onVolumeAdjusted: function(vol) {
                        if (root.ps) {
                            root.ps.setVolume(vol)
                            if (root.notif) root.notif.showMessage("Volumen: " + vol + "%", "info")
                        }
                    }
                    onMuteClicked: {
                        if (root.ps) {
                            root.ps.toggleMute()
                            if (root.notif) root.notif.showMessage(root.ps.muted ? "Silenciado" : "Sonido activado", "info")
                        }
                    }
                }
            }
        }
    }
}
