import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"

Item {
    id: root
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Bar"
    objectName: "nowPlayingBar"
    focus: true

    property var ps: typeof nowplayingBridge !== "undefined" && nowplayingBridge
                     ? nowplayingBridge
                     : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var outputBridge: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _backendAvailable: root.ps ? root.ps.backendAvailable : false
    property string _lastShownError: ""
    readonly property bool compactLayout: width < MichiTheme.breakpoints.compact
    readonly property bool mediumLayout: width >= MichiTheme.breakpoints.compact
                                         && width < MichiTheme.breakpoints.medium
    readonly property string layoutMode: compactLayout ? "compact" : mediumLayout ? "medium" : "desktop"

    function bridgeValue(name, fallbackValue) {
        if (!root.ps) return fallbackValue
        var value = root.ps[name]
        return typeof value === "undefined" ? fallbackValue : value
    }

    implicitHeight: {
        if (compactLayout) return MichiTheme.nowPlaying.compact
        if (mediumLayout) return MichiTheme.nowPlaying.medium
        return MichiTheme.nowPlaying.desktop
    }
    height: implicitHeight
    clip: true

    Connections {
        target: root.ps
        ignoreUnknownSignals: true
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

            NowPlayingSeekBar {
                id: seekBar
                objectName: "nowPlayingProgress"
                Layout.fillWidth: true
                Layout.preferredHeight: 20
                position: root.ps ? root.ps.position : 0
                duration: root.ps ? root.ps.duration : 0
                enabled: root._hasTrack && (root.ps ? root.ps.seekSupported : false)
                onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
            }

            RowLayout {
                id: desktopBody
                objectName: "nowPlayingDesktopBody"
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: !root.compactLayout
                spacing: MichiTheme.spacing.md

                // Left: metadata (fills equally to center transport)
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    spacing: MichiTheme.spacing.md

                    CoverImage {
                        Layout.preferredWidth: 68
                        Layout.preferredHeight: 68
                        coverRadius: MichiTheme.radius.sm
                        coverKey: root.ps ? root.ps.coverPath : ""
                        showPlaceholder: true

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("playback")
                            Accessible.name: qsTr("Abrir reproducción")
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2

                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                            color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                            elide: Text.ElideRight

                            MouseArea {
                                anchors.fill: parent
                                enabled: root._hasTrack
                                onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("playback")
                                Accessible.name: qsTr("Abrir reproducción")
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps ? root.ps.trackArtist : qsTr("Abre la biblioteca para elegir")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.secondarySize
                            elide: Text.ElideRight
                        }
                    }

                    MichiButton {
                        text: qsTr("Explorar")
                        variant: "ghost"
                        visible: !root._hasTrack
                        onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("library")
                        Accessible.name: qsTr("Explorar biblioteca")
                    }
                }

                // Center: transport (truly centered on viewport)
                NowPlayingTransport {
                    Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                    compact: false
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    playPauseSupported: root._hasTrack && (root.ps ? root.ps.playPauseSupported : false)
                    previousSupported: root._hasTrack && (root.ps ? root.ps.previousSupported : false)
                    nextSupported: root._hasTrack && (root.ps ? root.ps.nextSupported : false)
                    shuffleSupported: root._hasTrack && (root.ps ? root.ps.shuffleSupported : false)
                    repeatSupported: root._hasTrack && (root.ps ? root.ps.repeatSupported : false)
                    onPlayClicked: if (root.ps) root.ps.togglePlay()
                    onPrevClicked: if (root.ps) root.ps.previous()
                    onNextClicked: if (root.ps) root.ps.next()
                    onShuffleClicked: if (root.ps) root.ps.toggleShuffle()
                    onRepeatClicked: if (root.ps) root.ps.toggleRepeat()
                }

                // Right: utilities (fills equally to center transport)
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    spacing: MichiTheme.spacing.xs

                    NowPlayingQualityBadge {
                        visible: root.width >= 1300 && root._hasTrack
                        available: root.bridgeValue("qualityInfoAvailable", false)
                        loading: root.bridgeValue("qualityLoading", false)
                        error: root.bridgeValue("qualityError", "") !== ""
                        sourceType: root.bridgeValue("sourceType", "")
                        formatLabel: root.bridgeValue("formatLabel", "")
                        qualityLabel: root.bridgeValue("qualityLabel", "")
                        sampleRate: root.bridgeValue("sampleRate", "")
                        bitDepth: root.bridgeValue("bitDepth", "")
                        channels: root.bridgeValue("channels", "")
                        bitrate: root.bridgeValue("bitrate", "")
                        onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("playback")
                    }

                    NowPlayingUtilityControls {
                        eqSupported: root._hasTrack && (typeof capabilityBridge !== "undefined" && capabilityBridge ? capabilityBridge.has("eq") : true)
                        transmitSupported: root._hasTrack && (typeof capabilityBridge !== "undefined" && capabilityBridge ? capabilityBridge.has("transmit") : false)
                        queueSupported: root._hasTrack && root.bridgeValue("queueSupported", false)
                        showMiniPlayer: root.width >= 1180
                        onEqClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("equalizer")
                        onTransmitClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("home_audio")
                        onOutputClicked: outputPopup.open()
                        onQueueClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("queue")
                        onMiniPlayerClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("playback")
                    }

                    NowPlayingVolume {
                        Layout.preferredWidth: 140
                        volume: root.ps ? root.ps.volume : 80
                        muted: root.ps ? root.ps.muted : false
                        volumeSupported: root._hasTrack && (root.ps ? root.ps.volumeSupported : false)
                        muteSupported: root._hasTrack && (root.ps ? root.ps.muteSupported : false)
                        onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                        onMuteClicked: if (root.ps) root.ps.toggleMute()
                    }
                }
            }

            ColumnLayout {
                id: compactBody
                objectName: "nowPlayingCompactBody"
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.compactLayout
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    spacing: MichiTheme.spacing.sm

                    CoverImage {
                        Layout.preferredWidth: 36
                        Layout.preferredHeight: 36
                        coverRadius: MichiTheme.radius.sm
                        coverKey: root.ps ? root.ps.coverPath : ""
                        showPlaceholder: true
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightSemiBold
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps ? root.ps.trackArtist : ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.secondarySize
                            elide: Text.ElideRight
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Item { Layout.fillWidth: true }
                    NowPlayingTransport {
                        compact: true
                        isPlaying: root.ps ? root.ps.isPlaying : false
                        shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                        repeatMode: root.ps ? root.ps.repeatMode : "none"
                        playPauseSupported: root._hasTrack && (root.ps ? root.ps.playPauseSupported : false)
                        previousSupported: root._hasTrack && (root.ps ? root.ps.previousSupported : false)
                        nextSupported: root._hasTrack && (root.ps ? root.ps.nextSupported : false)
                        shuffleSupported: root._hasTrack && (root.ps ? root.ps.shuffleSupported : false)
                        repeatSupported: root._hasTrack && (root.ps ? root.ps.repeatSupported : false)
                        onPlayClicked: if (root.ps) root.ps.togglePlay()
                        onPrevClicked: if (root.ps) root.ps.previous()
                        onNextClicked: if (root.ps) root.ps.next()
                        onShuffleClicked: if (root.ps) root.ps.toggleShuffle()
                        onRepeatClicked: if (root.ps) root.ps.toggleRepeat()
                    }
                    NowPlayingVolume {
                        Layout.preferredWidth: 140
                        visible: root.width >= 620
                        volume: root.ps ? root.ps.volume : 80
                        muted: root.ps ? root.ps.muted : false
                        volumeSupported: root._hasTrack && (root.ps ? root.ps.volumeSupported : false)
                        muteSupported: root._hasTrack && (root.ps ? root.ps.muteSupported : false)
                        onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                        onMuteClicked: if (root.ps) root.ps.toggleMute()
                    }
                    Item { Layout.fillWidth: true }
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
                text: qsTr("Salida de audio")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Repeater {
                model: root.outputBridge ? root.outputBridge.profiles : []
                Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 36
                    radius: MichiTheme.radius.sm
                    color: modelData.active ? MichiTheme.colors.accentSurface : "transparent"
                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.rightMargin: MichiTheme.spacing.sm
                        text: modelData.label || modelData.name || ""
                        color: modelData.active ? MichiTheme.colors.accent : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
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
                }
            }

            Text {
                text: root.outputBridge && (!root.outputBridge.profiles || root.outputBridge.profiles.length === 0)
                      ? qsTr("No hay perfiles disponibles") : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }
        }
    }
}
