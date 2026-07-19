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
    readonly property bool compactLayout: width < 900

    function bridgeValue(name, fallbackValue) {
        if (!root.ps) return fallbackValue
        var value = root.ps[name]
        return typeof value === "undefined" ? fallbackValue : value
    }

    function navigateTo(route) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate(route)
    }

    function openOutputSelector() {
        if (!root.outputBridge)
            return
        var result = root.outputBridge.refresh()
        if (result && result.ok === false) {
            if (root.notif) root.notif.showMessage(result.error || qsTr("No se pudieron cargar las salidas"), "warning")
            return
        }
        outputPopup.open()
    }

    function applyOutputProfile(profileId) {
        if (!root.outputBridge)
            return
        var result = root.outputBridge.setActiveProfile(profileId)
        if (result && result.ok === false && root.notif)
            root.notif.showMessage(result.message || result.error || qsTr("No se pudo cambiar la salida"), "error")
        else
            outputPopup.close()
    }

    function openTransmit() {
        root.navigateTo("home_audio")
    }

    implicitHeight: compactLayout ? 128 : 112
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
                Layout.preferredHeight: 24
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

                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 220
                    Layout.maximumWidth: 360
                    spacing: MichiTheme.spacing.md

                    CoverImage {
                        Layout.preferredWidth: 64
                        Layout.preferredHeight: 64
                        coverRadius: MichiTheme.radius.sm
                        coverKey: root.ps ? root.ps.coverPath : ""
                        showPlaceholder: true
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2

                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                            color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightSemiBold
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack
                                  ? root.bridgeValue("formatLabel", qsTr("Audio local"))
                                  : qsTr("Biblioteca Michi")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._hasTrack && root.ps ? root.ps.trackArtist : qsTr("Selecciona una canción para comenzar")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.secondarySize
                            elide: Text.ElideRight
                        }
                    }
                }

                Item {
                    Layout.preferredWidth: 258
                    Layout.fillHeight: true

                    NowPlayingTransport {
                        anchors.centerIn: parent
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
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 310
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
                        onClicked: root.navigateTo("playback")
                    }

                    NowPlayingUtilityControls {
                        eqSupported: root._hasTrack && typeof eqBridge !== "undefined" && eqBridge && eqBridge.backendAvailable
                        transmitSupported: false
                        outputSupported: root.outputBridge !== null
                        queueSupported: root._hasTrack && root.bridgeValue("queueSupported", false)
                        showMiniPlayer: root.width >= 1180
                        onEqClicked: root.navigateTo("equalizer")
                        onTransmitClicked: root.openTransmit()
                        onOutputClicked: root.openOutputSelector()
                        onQueueClicked: root.navigateTo("queue")
                        onMiniPlayerClicked: root.navigateTo("playback")
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
                    spacing: MichiTheme.spacing.xs

                    NowPlayingUtilityControls {
                        eqSupported: root._hasTrack && typeof eqBridge !== "undefined" && eqBridge && eqBridge.backendAvailable
                        transmitSupported: false
                        outputSupported: root.outputBridge !== null
                        queueSupported: root._hasTrack && root.bridgeValue("queueSupported", false)
                        showMiniPlayer: false
                        onEqClicked: root.navigateTo("equalizer")
                        onTransmitClicked: root.openTransmit()
                        onOutputClicked: root.openOutputSelector()
                        onQueueClicked: root.navigateTo("queue")
                    }
                    Item { Layout.fillWidth: true; Layout.minimumWidth: 0 }
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
                        visible: root.width >= 680
                        volume: root.ps ? root.ps.volume : 80
                        muted: root.ps ? root.ps.muted : false
                        volumeSupported: root._hasTrack && (root.ps ? root.ps.volumeSupported : false)
                        muteSupported: root._hasTrack && (root.ps ? root.ps.muteSupported : false)
                        onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                        onMuteClicked: if (root.ps) root.ps.toggleMute()
                    }
                    Item { Layout.fillWidth: true; Layout.minimumWidth: 0 }
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
                    color: root.outputBridge && root.outputBridge.activeProfileId === modelData.id
                           ? MichiTheme.colors.accentSurface : "transparent"
                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.rightMargin: MichiTheme.spacing.sm
                        text: modelData.label || modelData.name || ""
                        color: root.outputBridge && root.outputBridge.activeProfileId === modelData.id
                               ? MichiTheme.colors.accent : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.applyOutputProfile(modelData.id || modelData.key || "")
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
