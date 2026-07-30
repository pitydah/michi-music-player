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
    Accessible.description: "Barra de reproducción con controles de play/pause, siguiente, anterior, volumen y seek"
    objectName: "nowPlayingBar"
    focus: true

    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var outputBridge: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _backendAvailable: root.ps ? root.ps.backendAvailable : false
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
        return parts.join(" \u00B7 ")
    }

    function bridgeValue(name, fallbackValue) {
        if (!root.ps) return fallbackValue
        var value = root.ps[name]
        return typeof value === "undefined" ? fallbackValue : value
    }

    function openTrackContext() {
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate(root._hasTrack ? "playback" : "library")
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
                                        return root.ps.trackArtist + " \u00B7 " + root.ps.trackAlbum
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

                    PlaybackProgress {
                        id: seekBar
                        objectName: "nowPlayingProgress"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: Math.round(parent.height * 0.38)
                        position: root.ps ? root.ps.position : 0
                        duration: root.ps ? root.ps.duration : 0
                        seekable: root._hasTrack && (root.ps ? root.ps.seekSupported : false)
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
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            compact: false
                            isPlaying: root.ps ? root.ps.isPlaying : false
                            shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                            repeatMode: root.ps ? root.ps.repeatMode : "none"
                            commandPending: !root._hasTrack
                                            || (root.ps ? root.ps.commandPending || !root.ps.playPauseSupported : true)
                            showPrevious: root._hasTrack && (root.ps ? root.ps.previousSupported : false)
                            showNext: root._hasTrack && (root.ps ? root.ps.nextSupported : false)
                            showShuffle: root._hasTrack && (root.ps ? root.ps.shuffleSupported : false)
                            showRepeat: root._hasTrack && (root.ps ? root.ps.repeatSupported : false)
                            onPlayRequested: if (root.ps) root.ps.togglePlay()
                            onPauseRequested: if (root.ps) root.ps.togglePlay()
                            onPreviousRequested: if (root.ps) root.ps.previous()
                            onNextRequested: if (root.ps) root.ps.next()
                            onShuffleToggled: if (root.ps) root.ps.toggleShuffle()
                            onRepeatCycled: if (root.ps) root.ps.toggleRepeat()
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

                PlaybackProgress {
                    id: compactSeekBar
                    anchors.left: compactMetadataCard.right
                    anchors.leftMargin: MichiTheme.spacing.sm
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: Math.round(parent.height * 0.38)
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    seekable: root._hasTrack && (root.ps ? root.ps.seekSupported : false)
                    compact: true
                    onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                }

                PlaybackTransport {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: compactSeekBar.bottom
                    anchors.bottom: parent.bottom
                    compact: true
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    commandPending: !root._hasTrack
                                    || (root.ps ? root.ps.commandPending || !root.ps.playPauseSupported : true)
                    showPrevious: root._hasTrack && (root.ps ? root.ps.previousSupported : false)
                    showNext: root._hasTrack && (root.ps ? root.ps.nextSupported : false)
                    onPlayRequested: if (root.ps) root.ps.togglePlay()
                    onPauseRequested: if (root.ps) root.ps.togglePlay()
                    onPreviousRequested: if (root.ps) root.ps.previous()
                    onNextRequested: if (root.ps) root.ps.next()
                }
            }
        }
    }

    OutputProfileMenu {
        id: outputPopup
        x: Math.round(parent.width - width - MichiTheme.spacing.md)
        y: Math.round(-height - MichiTheme.spacing.sm)
        outputBridge: root.outputBridge
    }
}
