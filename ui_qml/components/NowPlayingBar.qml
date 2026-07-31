import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"

/* NowPlayingBar — canonical playback bar (two-row reference layout).
 *
 * Units: position/duration are SECONDS (GStreamer ns→s in player.py:797).
 * PlaybackProgress and seek() both consume seconds, so no /1000 conversion
 * is performed here.
 */
Item {
    id: root
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Now Playing Bar")
    Accessible.description: qsTr("Barra de reproducción con controles de play/pause, siguiente, anterior, volumen y seek")
    objectName: "nowPlayingBar"
    focus: true

    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var outputProfilesBridgeRef: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property var audioOutputBridgeRef: typeof audioOutputBridge !== "undefined" ? audioOutputBridge : null
    property string densityMode: ""
    property string _lastShownError: ""
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _backendAvailable: root.ps ? root.ps.backendAvailable : false

    /* Layout is driven by densityMode when AppShell assigns it; otherwise it
     * is derived from the bar's own width (used by the offscreen layout tests). */
    readonly property bool compactLayout: densityMode === "compact"
                                          || (densityMode === "" && width < MichiTheme.breakpoints.compact)
    readonly property bool mediumLayout: densityMode === "reduced"
                                         || (densityMode === "" && width >= MichiTheme.breakpoints.compact
                                             && width < MichiTheme.breakpoints.medium)
    readonly property int metadataCardWidth: mediumLayout ? 210 : 270
    readonly property int technicalColumnWidth: 260
    readonly property int edgeInset: MichiTheme.spacing.md

    readonly property string sourceLabel: {
        var source = root.bridgeValue("sourceType", "")
        if (source === "local_file") return qsTr("LOCAL")
        if (source === "michi_server") return qsTr("MICHI SERVER")
        if (source === "network_share") return qsTr("RED")
        if (source === "remote") return qsTr("REMOTO")
        if (source === "radio") return qsTr("RADIO")
        if (source === "disc") return qsTr("DISCO")
        return source ? source.toUpperCase() : qsTr("SIN FUENTE")
    }
    readonly property string technicalLabel: {
        var parts = [root.sourceLabel]
        var format = root.bridgeValue("formatLabel", "")
        if (format) parts.push(format.toUpperCase())
        return parts.join(" · ")
    }

    /* Effective playback/backend state color for the metadata card dot.
     * Shares the same bridge inputs (playbackStatus, backendState) as the
     * NowPlayingPage PlaybackStatusIndicator so both surfaces agree. */
    readonly property color playbackStateColor: {
        if (!root.ps || !root._hasTrack)
            return MichiTheme.colors.textMuted
        var bstate = root.ps.backendState
        if (bstate === "failed" || bstate === "unavailable")
            return MichiTheme.colors.error
        if (bstate === "degraded")
            return MichiTheme.colors.warning
        var status = root.ps.playbackStatus
        if (status === "failed" || status === "error")
            return MichiTheme.colors.error
        if (status === "reconnecting" || status === "buffering"
                || status === "loading" || bstate === "initializing")
            return MichiTheme.colors.warning
        if (status === "playing")
            return MichiTheme.colors.nowPlayingGradientMiddle
        if (status === "paused")
            return MichiTheme.colors.accentBlue
        return MichiTheme.colors.textMuted
    }

    function bridgeValue(name, fallbackValue) {
        if (!root.ps) return fallbackValue
        var value = root.ps[name]
        return typeof value === "undefined" ? fallbackValue : value
    }
    function openTrackContext() {
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate(root._hasTrack ? "nowplaying" : "library")
    }

    implicitHeight: compactLayout ? MichiTheme.nowPlaying.compact
                    : mediumLayout ? MichiTheme.nowPlaying.medium
                                   : MichiTheme.nowPlaying.desktop
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
    }

    /* Background */
    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.nowPlayingBackground
        Rectangle {
            anchors.top: parent.top; width: parent.width; height: 1
            color: MichiTheme.colors.nowPlayingBorder
        }
    }

    /* ── Desktop / medium layout (two-row reference) ── */
    Item {
        id: desktopSurface
        objectName: "nowPlayingReferenceLayout"
        anchors.fill: parent
        anchors.leftMargin: root.edgeInset
        anchors.rightMargin: root.edgeInset
        visible: !root.compactLayout

        Rectangle {
            id: metadataCard
            objectName: "nowPlayingMetadataCard"
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: root.metadataCardWidth
            height: 86
            radius: 16
            color: metadataMouse.containsMouse ? MichiTheme.colors.nowPlayingTransportHover : MichiTheme.colors.surfaceCard
            border { width: 1; color: metadataMouse.containsMouse ? MichiTheme.colors.nowPlayingTransportHoverBorder : MichiTheme.colors.nowPlayingQualityBorder }
            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }

            Rectangle {
                x: 12; y: 11; width: 64; height: 64; radius: 10
                color: MichiTheme.colors.nowPlayingTransportBg
                border { width: 1; color: root._hasTrack ? MichiTheme.colors.nowPlayingTransportHoverBorder : MichiTheme.colors.nowPlayingTransportBorder }
                CoverImage {
                    anchors.fill: parent; anchors.margins: 2
                    coverRadius: 8; coverKey: root.ps ? root.ps.coverPath : ""; showPlaceholder: true
                }
                Rectangle {
                    x: parent.width - 10; y: parent.height - 10; width: 10; height: 10; radius: 5
                    color: MichiTheme.colors.nowPlayingTransportBg
                    border { width: 1; color: MichiTheme.colors.nowPlayingTransportHoverBorder }
                    Rectangle { objectName: "nowPlayingStateDot"
                        width: 5; height: 5; radius: 3; anchors.centerIn: parent
                        color: root.playbackStateColor }
                }
            }
            Text {
                x: 90; y: 17; width: parent.width - 106
                text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                font { pixelSize: 14; weight: Font.DemiBold }
                elide: Text.ElideRight; maximumLineCount: 1
            }
            Text {
                x: 90; y: 40; width: parent.width - 106
                text: {
                    if (!root._hasTrack || !root.ps) return qsTr("Añade música")
                    if (root.ps.trackArtist && root.ps.trackAlbum)
                        return root.ps.trackArtist + " · " + root.ps.trackAlbum
                    return root.ps.trackArtist || root.ps.trackAlbum || qsTr("Artista desconocido")
                }
                color: MichiTheme.colors.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight; maximumLineCount: 1
            }
            Text {
                x: 90; y: 61; width: parent.width - 106
                text: root._hasTrack ? root.technicalLabel : qsTr("BIBLIOTECA LOCAL")
                color: MichiTheme.colors.textMuted
                font { pixelSize: 10; weight: Font.Medium; letterSpacing: 0.6 }
                elide: Text.ElideRight; maximumLineCount: 1
            }
            MouseArea {
                id: metadataMouse; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.openTrackContext()
            }
            Accessible.role: Accessible.Button
            Accessible.name: root._hasTrack && root.ps ? qsTr("Abrir reproducción de %1").arg(root.ps.trackTitle) : qsTr("Explorar biblioteca")
            activeFocusOnTab: true
            Keys.onSpacePressed: root.openTrackContext()
            Keys.onReturnPressed: root.openTrackContext()
        }

        Item {
            id: primaryArea
            objectName: "nowPlayingPrimaryArea"
            anchors.left: metadataCard.right
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.right: technicalArea.left
            anchors.rightMargin: MichiTheme.spacing.md
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            PlaybackProgress {
                id: seekBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.round(parent.height * 0.42)
                position: root.ps ? root.ps.position : 0
                duration: root.ps ? root.ps.duration : 0
                seekable: root.ps ? root.ps.seekSupported : false
                enabled: root._hasTrack
                onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
            }

            Item {
                id: lowerPrimaryRow
                objectName: "nowPlayingLowerPrimaryRow"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: seekBar.bottom
                anchors.bottom: parent.bottom

                PlaybackTransport {
                    id: desktopTransport
                    objectName: "nowPlayingCenteredTransport"
                    anchors.centerIn: parent
                    variant: "bar"
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    commandPending: !root._hasTrack || (root.ps ? root.ps.commandPending : true)
                    /* Real capability flags; always visible when no track
                     * (cf202b8a: buttons stay visible, just disabled). */
                    showShuffle: !root._hasTrack || (root.ps ? root.ps.shuffleSupported : true)
                    showPrevious: !root._hasTrack || (root.ps ? root.ps.previousSupported : true)
                    showNext: !root._hasTrack || (root.ps ? root.ps.nextSupported : true)
                    showRepeat: !root._hasTrack || (root.ps ? root.ps.repeatSupported : true)
                    onPlayRequested: if (root.ps) root.ps.togglePlay()
                    onPauseRequested: if (root.ps) root.ps.togglePlay()
                    onPreviousRequested: if (root.ps) root.ps.previous()
                    onNextRequested: if (root.ps) root.ps.next()
                    onShuffleToggled: if (root.ps) root.ps.toggleShuffle()
                    onRepeatCycled: if (root.ps) root.ps.toggleRepeat()
                }
            }
        }

        Item {
            id: technicalArea
            objectName: "nowPlayingTechnicalArea"
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: root.technicalColumnWidth

            Row {
                id: upperTechnicalRow
                objectName: "nowPlayingUpperTechnicalRow"
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: Math.round((parent.height * 0.42 - height) / 2)
                spacing: MichiTheme.spacing.sm

                NowPlayingVolume {
                    width: 140
                    volume: root.ps ? root.ps.volume : 80
                    muted: root.ps ? root.ps.muted : false
                    volumeSupported: root._backendAvailable && (root.ps ? root.ps.volumeSupported : false)
                    muteSupported: root._backendAvailable && (root.ps ? root.ps.muteSupported : false)
                    onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                    onMuteClicked: if (root.ps) root.ps.toggleMute()
                }

                MichiIconButton {
                    controlObjectName: "eqButton"
                    iconKey: "eq"
                    iconVisualSize: 20
                    btnSize: 40
                    symbolicColor: MichiTheme.colors.textPrimary
                    enabled: typeof capabilityBridge === "undefined" || !capabilityBridge || capabilityBridge.has("eq")
                    Accessible.name: qsTr("Ecualizador"); tooltipText: qsTr("Ecualizador")
                    onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("equalizer")
                }

                MichiIconButton {
                    controlObjectName: "transmitButton"
                    iconKey: "streaming"
                    iconVisualSize: 20
                    btnSize: 40
                    symbolicColor: MichiTheme.colors.textPrimary
                    enabled: root._hasTrack
                    Accessible.name: qsTr("Transmitir"); tooltipText: qsTr("Transmitir")
                    onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("home_audio")
                }
            }

            Item {
                id: lowerUtilities
                objectName: "nowPlayingLowerUtilities"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: Math.round(parent.height * 0.58)

                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.sm

                    MichiIconButton {
                        controlObjectName: "audioOutputButton"
                        iconKey: "outputs"
                        iconVisualSize: 20
                        btnSize: 40
                        symbolicColor: MichiTheme.colors.textPrimary
                        enabled: root._backendAvailable
                        Accessible.name: qsTr("Elegir salida de audio"); tooltipText: qsTr("Elegir salida de audio")
                        onClicked: {
                            if (root.audioOutputBridgeRef !== null)
                                outputPopup.open()
                            else if (typeof navigationBridge !== "undefined")
                                navigationBridge.navigate("outputs")
                        }
                    }

                    MichiIconButton {
                        controlObjectName: "outputProfileButton"
                        iconKey: "settings"
                        iconVisualSize: 20
                        btnSize: 40
                        symbolicColor: MichiTheme.colors.textPrimary
                        enabled: root.outputProfilesBridgeRef !== null
                        Accessible.name: qsTr("Elegir perfil de salida"); tooltipText: qsTr("Elegir perfil de salida")
                        onClicked: profilePopup.open()
                    }

                    PlaybackQualityBadge {
                        active: root._hasTrack
                        label: root.technicalLabel
                        maximumWidth: Math.min(150, Math.max(80, root.technicalColumnWidth - 96))
                    }
                }
            }
        }
    }

    /* ── Compact layout ── */
    Item {
        id: compactSurface
        objectName: "nowPlayingCompactBody"
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.sm
        visible: root.compactLayout

        Rectangle {
            id: compactMetadataCard
            objectName: "nowPlayingCompactMetadataCard"
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(218, parent.width * 0.34)
            height: 48
            radius: 8
            color: MichiTheme.colors.surfaceCard
            border { width: 1; color: MichiTheme.colors.nowPlayingQualityBorder }
            Row { spacing: 8; anchors.fill: parent; anchors.margins: 6
                CoverImage { width: 34; height: 34; coverRadius: 6
                    coverKey: root.ps ? root.ps.coverPath : ""; showPlaceholder: true }
                Column { width: parent.width - 48; spacing: 0
                    Text { width: parent.width; text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                        color: MichiTheme.colors.textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideRight }
                    Text { width: parent.width; text: root._hasTrack && root.ps ? root.ps.trackArtist : qsTr("Añade música")
                        color: MichiTheme.colors.textMuted; font.pixelSize: 10; elide: Text.ElideRight }
                }
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.openTrackContext() }
        }

        PlaybackTransport {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            compact: true
            isPlaying: root.ps ? root.ps.isPlaying : false
            shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
            repeatMode: root.ps ? root.ps.repeatMode : "none"
            commandPending: !root._hasTrack || (root.ps ? root.ps.commandPending : true)
            showPrevious: !root._hasTrack || (root.ps ? root.ps.previousSupported : true)
            showNext: !root._hasTrack || (root.ps ? root.ps.nextSupported : true)
            onPlayRequested: if (root.ps) root.ps.togglePlay()
            onPauseRequested: if (root.ps) root.ps.togglePlay()
            onPreviousRequested: if (root.ps) root.ps.previous()
            onNextRequested: if (root.ps) root.ps.next()
        }
    }

    AudioOutputMenu {
        id: outputPopup
        x: parent.width - width - 48; y: -height - 8
        outputBridge: root.audioOutputBridgeRef
    }
    OutputProfileMenu {
        id: profilePopup
        x: parent.width - width - 100; y: -height - 8
        outputBridge: root.outputProfilesBridgeRef
    }
}
