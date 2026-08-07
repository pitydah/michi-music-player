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
<<<<<<< Updated upstream

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

=======
    property string _lastShownError: ""
    readonly property bool compactLayout: width < MichiTheme.breakpoints.compact
    readonly property bool mediumLayout: width >= MichiTheme.breakpoints.compact
                                         && width < MichiTheme.breakpoints.medium
    readonly property string layoutMode: compactLayout ? "compact" : mediumLayout ? "medium" : "desktop"
    readonly property int technicalColumnWidth: compactLayout
                                                ? 0
                                                : mediumLayout
                                                  ? 252
                                                  : 280
    readonly property int metadataCardWidth: compactLayout
                                             ? 218
                                             : mediumLayout
                                               ? width < 960 ? 210 : 246
                                               : 284
    readonly property int edgeInset: compactLayout
                                     ? MichiTheme.spacing.sm
                                     : MichiTheme.spacing.md
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

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
=======
>>>>>>> Stashed changes

    function bridgeValue(name, fallbackValue) {
        if (!root.ps) return fallbackValue
        var value = root.ps[name]
        return typeof value === "undefined" ? fallbackValue : value
    }
<<<<<<< Updated upstream
    function openTrackContext() {
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate(root._hasTrack ? "nowplaying" : "library")
=======

    function openTrackContext() {
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate(root._hasTrack ? "playback" : "library")
    }

    implicitHeight: {
        if (compactLayout) return MichiTheme.nowPlaying.compact
        if (mediumLayout) return MichiTheme.nowPlaying.medium
        return MichiTheme.nowPlaying.desktop
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
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
=======
        Item {
            anchors.fill: parent
            anchors.leftMargin: root.edgeInset
            anchors.rightMargin: root.edgeInset
            anchors.topMargin: MichiTheme.spacing.xs
            anchors.bottomMargin: MichiTheme.spacing.xs

            Item {
                id: desktopSurface
                objectName: "nowPlayingReferenceLayout"
                anchors.fill: parent
                visible: !root.compactLayout

                Rectangle {
                    id: metadataCard
                    objectName: "nowPlayingMetadataCard"
                    width: root.metadataCardWidth
                    height: Math.min(94, parent.height - MichiTheme.spacing.md * 2)
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    radius: MichiTheme.radius.lg
                    color: metadataMouse.containsMouse
                           ? MichiTheme.colors.nowPlayingTransportHover
                           : MichiTheme.colors.surfaceCard
                    border.width: 1
                    border.color: metadataMouse.containsMouse
                                  ? MichiTheme.colors.nowPlayingTransportHoverBorder
                                  : MichiTheme.colors.nowPlayingQualityBorder
                    clip: true

                    Behavior on color {
                        ColorAnimation { duration: MichiTheme.motion.durationFast }
                    }
                    Behavior on border.color {
                        ColorAnimation { duration: MichiTheme.motion.durationFast }
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: metadataCard.radius - 1
                        color: "transparent"
                        border.width: 1
                        border.color: MichiTheme.colors.borderInner
                    }

                    Rectangle {
                        width: 3
                        height: parent.height - MichiTheme.spacing.lg * 2
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        radius: MichiTheme.radius.pill
                        visible: root._hasTrack
                        gradient: Gradient {
                            GradientStop {
                                position: 0
                                color: MichiTheme.colors.nowPlayingGradientStart
                            }
                            GradientStop {
                                position: 0.5
                                color: MichiTheme.colors.nowPlayingGradientMiddle
                            }
                            GradientStop {
                                position: 1
                                color: MichiTheme.colors.nowPlayingGradientEnd
                            }
                        }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.md

                        Item {
                            Layout.preferredWidth: metadataCard.height - MichiTheme.spacing.lg
                            Layout.preferredHeight: Layout.preferredWidth

                            Rectangle {
                                anchors.fill: parent
                                radius: MichiTheme.radius.md
                                color: MichiTheme.colors.nowPlayingTransportBg
                                border.width: 1
                                border.color: root._hasTrack
                                              ? MichiTheme.colors.nowPlayingTransportHoverBorder
                                              : MichiTheme.colors.nowPlayingTransportBorder

                                CoverImage {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    coverRadius: MichiTheme.radius.md - 2
                                    coverKey: root.ps ? root.ps.coverPath : ""
                                    showPlaceholder: true
                                }
                            }

                            Rectangle {
                                width: 18
                                height: 18
                                radius: MichiTheme.radius.pill
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: -2
                                visible: root._hasTrack
                                color: MichiTheme.colors.nowPlayingTransportBg
                                border.width: 1
                                border.color: MichiTheme.colors.nowPlayingTransportHoverBorder

                                Rectangle {
                                    width: 7
                                    height: 7
                                    radius: MichiTheme.radius.pill
                                    anchors.centerIn: parent
                                    color: root.ps && root.ps.isPlaying
                                           ? MichiTheme.colors.nowPlayingGradientMiddle
                                           : MichiTheme.colors.textMuted
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 3

                            Text {
                                Layout.fillWidth: true
                                text: root._hasTrack && root.ps
                                      ? root.ps.trackTitle
                                      : qsTr("Sin reproducción")
                                color: root._hasTrack
                                       ? MichiTheme.colors.textPrimary
                                       : MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightSemiBold
                                elide: Text.ElideRight
                                maximumLineCount: 1
                            }

                            Text {
                                Layout.fillWidth: true
                                text: {
                                    if (!root._hasTrack || !root.ps)
                                        return qsTr("Añade música")
                                    if (root.ps.trackArtist && root.ps.trackAlbum)
                                        return root.ps.trackArtist + " · " + root.ps.trackAlbum
                                    return root.ps.trackArtist || root.ps.trackAlbum || qsTr("Artista desconocido")
                                }
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.secondarySize
                                elide: Text.ElideRight
                                maximumLineCount: 1
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xs

                                Rectangle {
                                    width: 5
                                    height: 5
                                    radius: MichiTheme.radius.pill
                                    color: root._hasTrack
                                           ? MichiTheme.colors.nowPlayingGradientStart
                                           : MichiTheme.colors.textMeta
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root._hasTrack
                                          ? root.technicalLabel
                                          : qsTr("BIBLIOTECA LOCAL")
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.badgeSize
                                    font.weight: MichiTheme.typography.weightMedium
                                    font.letterSpacing: 0.6
                                    elide: Text.ElideRight
                                    maximumLineCount: 1
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: metadataMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openTrackContext()
                    }

                    Accessible.role: Accessible.Button
                    Accessible.name: root._hasTrack && root.ps
                                     ? qsTr("Abrir reproducción de %1").arg(root.ps.trackTitle)
                                     : qsTr("Explorar biblioteca")
                    activeFocusOnTab: true
                    Keys.onSpacePressed: root.openTrackContext()
                    Keys.onReturnPressed: root.openTrackContext()
                }

                Item {
                    id: primaryArea
                    objectName: "nowPlayingPrimaryArea"
                    anchors.left: metadataCard.right
                    anchors.leftMargin: MichiTheme.spacing.lg
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.right: technicalArea.left

                    NowPlayingSeekBar {
                        id: seekBar
                        objectName: "nowPlayingProgress"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: Math.round(parent.height * 0.38)
                        position: root.ps ? root.ps.position : 0
                        duration: root.ps ? root.ps.duration : 0
                        enabled: root._hasTrack && (root.ps ? root.ps.seekSupported : false)
                        onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                    }

                    Item {
                        id: lowerPrimaryRow
                        objectName: "nowPlayingLowerPrimaryRow"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: seekBar.bottom
                        anchors.bottom: parent.bottom

                        NowPlayingTransport {
                            id: desktopTransport
                            objectName: "nowPlayingCenteredTransport"
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
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

                        NowPlayingUtilityControls {
                            objectName: "nowPlayingLowerUtilities"
                            anchors.right: parent.right
                            anchors.rightMargin: MichiTheme.spacing.md
                            anchors.verticalCenter: parent.verticalCenter
                            eqSupported: false
                            transmitSupported: root._hasTrack && (typeof capabilityBridge !== "undefined" && capabilityBridge ? capabilityBridge.has("transmit") : false)
                            queueSupported: root._hasTrack && root.bridgeValue("queueSupported", false)
                            showEq: false
                            showTransmit: true
                            showOutput: false
                            showQueue: true
                            showMiniPlayer: false
                            onTransmitClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("home_audio")
                            onQueueClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("queue")
                        }
                    }
                }

                Item {
                    id: technicalArea
                    objectName: "nowPlayingTechnicalArea"
                    width: root.technicalColumnWidth
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom

                    Row {
                        id: upperTechnicalRow
                        objectName: "nowPlayingUpperTechnicalRow"
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: Math.round((parent.height * 0.38 - height) / 2)
                        height: 44
                        spacing: MichiTheme.spacing.xs

                        NowPlayingVolume {
                            width: 140
                            anchors.verticalCenter: parent.verticalCenter
                            volume: root.ps ? root.ps.volume : 80
                            muted: root.ps ? root.ps.muted : false
                            volumeSupported: root._hasTrack && (root.ps ? root.ps.volumeSupported : false)
                            muteSupported: root._hasTrack && (root.ps ? root.ps.muteSupported : false)
                            onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                            onMuteClicked: if (root.ps) root.ps.toggleMute()
                        }

                        NowPlayingUtilityControls {
                            anchors.verticalCenter: parent.verticalCenter
                            eqSupported: root._hasTrack && (typeof capabilityBridge !== "undefined" && capabilityBridge ? capabilityBridge.has("eq") : true)
                            outputSupported: root._backendAvailable
                            showEq: true
                            showTransmit: false
                            showOutput: true
                            showQueue: false
                            showMiniPlayer: false
                            onEqClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("equalizer")
                            onOutputClicked: outputPopup.open()
                        }
                    }

                    Rectangle {
                        id: outputProfileButton
                        objectName: "nowPlayingOutputProfileButton"
                        anchors.right: parent.right
                        anchors.rightMargin: MichiTheme.spacing.lg
                        y: Math.round(parent.height * 0.38
                                      + ((parent.height * 0.62) - height) / 2)
                        width: Math.min(150, parent.width - MichiTheme.spacing.md * 2)
                        height: 34
                        radius: MichiTheme.radius.md
                        color: outputProfileMa.containsMouse
                               ? MichiTheme.colors.nowPlayingTransportHover
                               : MichiTheme.colors.nowPlayingTransportBg
                        border.width: 1
                        border.color: outputProfileMa.containsMouse
                                      ? MichiTheme.colors.nowPlayingTransportHoverBorder
                                      : MichiTheme.colors.nowPlayingTransportBorder

                        MouseArea {
                            id: outputProfileMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: outputPopup.open()
                        }

                        Accessible.role: Accessible.Button
                        Accessible.name: qsTr("Seleccionar perfil de salida")
                        activeFocusOnTab: true
                        Keys.onSpacePressed: outputPopup.open()
                        Keys.onReturnPressed: outputPopup.open()
                    }
                }
            }

            Item {
                id: compactSurface
                objectName: "nowPlayingCompactBody"
                anchors.fill: parent
                visible: root.compactLayout

                Rectangle {
                    id: compactMetadataCard
                    objectName: "nowPlayingCompactMetadataCard"
                    width: Math.min(root.metadataCardWidth, parent.width * 0.34)
                    height: 42
                    anchors.left: parent.left
                    anchors.top: parent.top
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceCard
                    border.width: 1
                    border.color: MichiTheme.colors.nowPlayingQualityBorder

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xs
                        spacing: MichiTheme.spacing.sm

                        CoverImage {
                            Layout.preferredWidth: 34
                            Layout.preferredHeight: 34
                            coverRadius: MichiTheme.radius.sm
                            coverKey: root.ps ? root.ps.coverPath : ""
                            showPlaceholder: true
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Text {
                                Layout.fillWidth: true
                                text: root._hasTrack && root.ps
                                      ? root.ps.trackTitle
                                      : qsTr("Sin reproducción")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.captionSize
                                font.weight: MichiTheme.typography.weightSemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root._hasTrack && root.ps
                                      ? root.ps.trackArtist
                                      : qsTr("Añade música")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.badgeSize
                                elide: Text.ElideRight
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openTrackContext()
                    }
                }

                NowPlayingSeekBar {
                    id: compactSeekBar
                    anchors.left: compactMetadataCard.right
                    anchors.leftMargin: MichiTheme.spacing.sm
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: Math.round(parent.height * 0.38)
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    enabled: root._hasTrack && (root.ps ? root.ps.seekSupported : false)
                    onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                }

                NowPlayingTransport {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: compactSeekBar.bottom
                    anchors.bottom: parent.bottom
                    compact: true
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

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
=======
>>>>>>> Stashed changes
            }
        }
    }

<<<<<<< Updated upstream
    /* ── Compact layout ── */
    Item {
        id: compactSurface
        objectName: "nowPlayingCompactBody"
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.sm
        visible: root.compactLayout
=======
    Component.onCompleted: {
        if (root.outputBridge && root.outputBridge.refresh)
            root.outputBridge.refresh()
    }

    Popup {
        id: outputPopup
        x: Math.round(parent.width - width - MichiTheme.spacing.md)
        y: Math.round(-height - MichiTheme.spacing.sm)
        width: 240
        height: Math.min(300, outputList.height + MichiTheme.spacing.lg * 2)
        padding: MichiTheme.spacing.md
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
>>>>>>> Stashed changes

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
