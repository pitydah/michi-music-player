import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Bar"
    objectName: "nowPlayingBar"
    focus: true
    id: root

    property var ps: typeof nowplayingBridge !== "undefined" && nowplayingBridge
                     ? nowplayingBridge
                     : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _backendAvailable: root.ps ? root.ps.backendAvailable : false
    property string _lastShownError: ""

    Connections {
        target: root.ps
        function onErrorChanged() {
            if (root.ps && root.ps.errorMessage && root.ps.errorMessage !== root._lastShownError && root.notif) {
                root._lastShownError = root.ps.errorMessage
                root.notif.showMessage(root.ps.errorMessage, "error")
            }
        }
        function onCommandStateChanged() {
            if (root.ps && root.ps.lastCommandError && root.ps.lastCommandMessage && root.notif)
                root.notif.showMessage(root.ps.lastCommandMessage, "warning")
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceNowPlaying
        Rectangle {
            anchors.top: parent.top
            width: parent.width; height: 1
            color: MichiTheme.colors.surfaceNowPlayingBorder
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            RowLayout {
                Layout.preferredWidth: parent.width * 0.22
                Layout.fillHeight: true
                spacing: MichiTheme.spacing.md

                NowPlayingCover {
                    id: coverArt
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                    coverKey: root.ps ? root.ps.coverPath : ""
                    placeholderMode: !root._hasTrack
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 3

                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps ? root.ps.trackTitle : "Sin reproducción"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: root._hasTrack ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps && root.ps.trackArtist
                                  ? root.ps.trackArtist + (root.ps.trackAlbum ? " · " + root.ps.trackAlbum : "")
                                  : "Selecciona una canción desde Biblioteca"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                        }
                    }

                    MouseArea {
                        objectName: "nowPlayingTrackInfoArea"
                        anchors.fill: parent
                        cursorShape: root._hasTrack ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (root._hasTrack && typeof navigationBridge !== "undefined")
                                navigationBridge.navigate("playback")
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredWidth: 1 }

            ColumnLayout {
                Layout.preferredWidth: parent.width * 0.40
                Layout.fillHeight: true
                spacing: 2

                NowPlayingControls {
                    Layout.alignment: Qt.AlignHCenter
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    playPauseSupported: root.ps ? root.ps.playPauseSupported : false
                    previousSupported: root.ps ? root.ps.previousSupported : false
                    nextSupported: root.ps ? root.ps.nextSupported : false
                    shuffleSupported: root.ps ? root.ps.shuffleSupported : false
                    repeatSupported: root.ps ? root.ps.repeatSupported : false
                    onPlayClicked: { if (root.ps) root.ps.togglePlay() }
                    onPrevClicked: { if (root.ps) root.ps.previous() }
                    onNextClicked: { if (root.ps) root.ps.next() }
                    onShuffleClicked: { if (root.ps) root.ps.toggleShuffle() }
                    onRepeatClicked: { if (root.ps) root.ps.toggleRepeat() }
                }

                NowPlayingSeekBar {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    enabled: root.ps ? root.ps.seekSupported : false
                    onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredWidth: 1 }

            RowLayout {
                Layout.preferredWidth: parent.width * 0.20
                Layout.maximumWidth: 160
                Layout.fillHeight: true
                layoutDirection: Qt.RightToLeft
                spacing: MichiTheme.spacing.sm

                NowPlayingVolume {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.fillWidth: true
                    Layout.maximumWidth: 120
                    volume: root.ps ? root.ps.volume : 80
                    muted: root.ps ? root.ps.muted : false
                    volumeSupported: root.ps ? root.ps.volumeSupported : false
                    muteSupported: root.ps ? root.ps.muteSupported : false
                    onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                    onMuteClicked: { if (root.ps) root.ps.toggleMute() }
                }

                MichiIconButton {
                    objectName: "nowPlayingOpenPlaybackButton"
                    iconText: ""
                    iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
                    tooltipText: "Reproducción"
                    btnSize: 22
                    Layout.alignment: Qt.AlignVCenter
                    onClicked: {
                        if (typeof navigationBridge !== "undefined") navigationBridge.navigate("playback")
                    }
                }
            }
        }
    }
}
