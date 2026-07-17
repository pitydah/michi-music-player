import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"

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
    property var outputBridge: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _backendAvailable: root.ps ? root.ps.backendAvailable : false
    property string _lastShownError: ""

    MichiResponsive { id: responsive; availableWidth: root.width }

    height: 116

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
        color: MichiTheme.colors.nowPlayingBackground

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: MichiTheme.colors.nowPlayingBorder
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: 0

            // ── Row 1: Seek + Volume + Utilities ──
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: responsive.compact ? 28 : 32
                Layout.topMargin: responsive.compact ? 4 : 6
                spacing: MichiTheme.spacing.sm

                NowPlayingSeekBar {
                    id: seekBar
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    enabled: root.ps ? root.ps.seekSupported : false
                    onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                }

                NowPlayingVolume {
                    id: volumeCtrl
                    Layout.alignment: Qt.AlignVCenter
                    visible: !responsive.compact
                    volume: root.ps ? root.ps.volume : 80
                    muted: root.ps ? root.ps.muted : false
                    volumeSupported: root.ps ? root.ps.volumeSupported : false
                    muteSupported: root.ps ? root.ps.muteSupported : false
                    onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                    onMuteClicked: { if (root.ps) root.ps.toggleMute() }
                }

                NowPlayingUtilityControls {
                    id: utilityCtrl
                    Layout.alignment: Qt.AlignVCenter
                    visible: !responsive.compact
                    eqSupported: true
                    transmitSupported: false
                    onEqClicked: {
                        if (typeof navigationBridge !== "undefined")
                            navigationBridge.navigate("equalizer")
                    }
                    onTransmitClicked: { }
                    onOutputClicked: outputPopup.open()
                    onMiniPlayerClicked: {
                        if (typeof navigationBridge !== "undefined")
                            navigationBridge.navigate("playback")
                    }
                }
            }

            // ── Row 2: Transport + Badge ──
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: responsive.compact ? 48 : 54
                Layout.bottomMargin: responsive.compact ? 6 : 8
                spacing: MichiTheme.spacing.md

                Item { Layout.preferredWidth: responsive.compact ? 0 : MichiTheme.spacing.xl }

                NowPlayingTransport {
                    id: transport
                    Layout.alignment: Qt.AlignVCenter
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

                Item { Layout.fillWidth: true }

                NowPlayingQualityBadge {
                    id: qualityBadge
                    Layout.alignment: Qt.AlignVCenter
                    visible: !responsive.compact
                    available: root.ps ? root.ps.qualityInfoAvailable : false
                    loading: root.ps ? root.ps.qualityLoading : false
                    error: root.ps ? root.ps.qualityError !== "" : false
                    sourceType: root.ps ? root.ps.sourceType : ""
                    formatLabel: root.ps ? root.ps.formatLabel : ""
                    qualityLabel: root.ps ? root.ps.qualityLabel : ""
                    sampleRate: root.ps ? root.ps.sampleRate : ""
                    bitDepth: root.ps ? root.ps.bitDepth : ""
                    channels: root.ps ? root.ps.channels : ""
                    bitrate: root.ps ? root.ps.bitrate : ""
                    onClicked: {
                        if (typeof navigationBridge !== "undefined")
                            navigationBridge.navigate("playback")
                    }
                }
            }
        }
    }

    Popup {
        id: outputPopup
        x: Math.round(parent.width - width - MichiTheme.spacing.md)
        y: Math.round(-height - MichiTheme.spacing.sm)
        width: 240
        height: Math.min(300, outputList.height + MichiTheme.spacing.lg * 2)
        padding: MichiTheme.spacing.md
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: MichiTheme.colors.surfacePopup
            radius: MichiTheme.radius.md
            border.width: 1
            border.color: MichiTheme.colors.borderCard
        }

        Column {
            id: outputList
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Salida de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Repeater {
                model: root.outputBridge ? root.outputBridge.profiles : []

                Rectangle {
                    width: parent.width
                    height: 32
                    radius: MichiTheme.radius.sm
                    color: modelData.active ? MichiTheme.colors.accentSurface : "transparent"

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.sm
                        text: modelData.label || modelData.name || ""
                        color: modelData.active ? MichiTheme.colors.accent : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        elide: Text.ElideRight
                        width: parent.width - MichiTheme.spacing.md
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.outputBridge && root.outputBridge.setActiveProfile)
                                root.outputBridge.setActiveProfile(modelData.id || modelData.key || "")
                            outputPopup.close()
                        }
                    }

                    Accessible.role: Accessible.Button
                    Accessible.name: modelData.label || modelData.name || ""
                }
            }

            Text {
                text: root.outputBridge && (!root.outputBridge.profiles || root.outputBridge.profiles.length === 0) ? "No hay perfiles disponibles" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }
        }
    }
}
