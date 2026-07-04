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
    property bool _panelExpanded: false

    height: MichiTheme.nowPlayingHeight + (_panelExpanded ? 280 : 0)
    visible: true

    Behavior on height { NumberAnimation { duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic } }

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            width: parent.width
            height: MichiTheme.nowPlayingHeight

            Rectangle {
                anchors.top: parent.top
                width: parent.width; height: 1
                color: MichiTheme.colors.surfaceNowPlayingBorder
            }

            Rectangle {
                anchors.top: parent.top
                width: 40; height: 2
                anchors.horizontalCenter: parent.horizontalCenter
                radius: 1; color: MichiTheme.colors.accentBlue; opacity: 0.4
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
                        placeholderMode: !root._hasTrack
                        opacity: root._hasTrack ? 1.0 : 0.5
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        Text {
                            text: root._hasTrack && root.ps ? root.ps.trackTitle : root._emptyLabel
                            color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: root._hasTrack ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                            elide: Text.ElideRight
                            width: parent.width - 60
                        }

                        Text {
                            text: root._hasTrack && root.ps && root.ps.trackArtist
                                  ? root.ps.trackArtist + (root.ps.trackAlbum ? " · " + root.ps.trackAlbum : "")
                                  : root._canPlay ? "Selecciona una canción desde Biblioteca" : "Playback no disponible"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            width: parent.width - 60
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        visible: !root._canPlay
                        StatusBadge { text: "Safe mode"; kind: "experimental" }
                    }
                }

                Column {
                    width: parent.width * 0.44; height: parent.height; spacing: 2

                    NowPlayingControls {
                        anchors.horizontalCenter: parent.horizontalCenter
                        isPlaying: root.ps ? root.ps.isPlaying : false
                        shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                        repeatMode: root.ps ? root.ps.repeatMode : "none"
                        enabled: root._canPlay && root._hasTrack
                        opacity: root._canPlay && root._hasTrack ? 1.0 : 0.35
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
                        position: root.ps ? root.ps.position : 0
                        duration: root.ps ? root.ps.duration : 0
                        enabled: root._canPlay && root._hasTrack && (root.ps ? root.ps.duration > 0 : false)
                        opacity: root._canPlay && root._hasTrack && (root.ps ? root.ps.duration > 0 : false) ? 1.0 : 0.35
                        onSeekRequested: function(pos) {
                            if (!root._canPlay) { if (root.notif) root.notif.showMessage("Playback no disponible", "warning"); return }
                            if (root.ps) root.ps.seek(pos)
                        }
                    }
                }

                Row {
                    width: parent.width * 0.22; height: parent.height
                    layoutDirection: Qt.RightToLeft

                    Column {
                        anchors.verticalCenter: parent.verticalCenter;
                        spacing: 4

                        NowPlayingVolume {
                            volume: root.ps ? root.ps.volume : 80
                            muted: root.ps ? root.ps.muted : false
                            enabled: root._canPlay
                            opacity: root._canPlay ? 1.0 : 0.35
                            onVolumeAdjusted: function(vol) {
                                if (!root._canPlay) { if (root.notif) root.notif.showMessage("Playback no disponible", "warning"); return }
                                if (root.ps) root.ps.setVolume(vol)
                            }
                            onMuteClicked: {
                                if (!root._canPlay) { if (root.notif) root.notif.showMessage("Playback no disponible", "warning"); return }
                                if (root.ps) root.ps.toggleMute()
                            }
                        }

                        Text {
                            text: "[+]"
                            color: MichiTheme.colors.textMuted; font.pixelSize: 10; opacity: 0.6
                            anchors.horizontalCenter: parent.horizontalCenter
                            visible: !root._panelExpanded
                        }
                        Text {
                            text: "[-]"
                            color: MichiTheme.colors.textMuted; font.pixelSize: 10; opacity: 0.6
                            anchors.horizontalCenter: parent.horizontalCenter
                            visible: root._panelExpanded
                        }
                    }
                }
            }

            MouseArea {
                anchors.left: parent.left; width: parent.width * 0.28
                anchors.top: parent.top; height: parent.height
                cursorShape: root._canPlay && root._hasTrack ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: { if (root._canPlay && root._hasTrack) root._panelExpanded = !root._panelExpanded }
            }
        }

        ExpandedNowPlayingPanel {
            width: parent.width
            ps: root.ps
            expanded: root._panelExpanded
            onClosePanel: root._panelExpanded = false
        }
    }
}
