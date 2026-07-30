import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"

/* NowPlayingBar — canonical playback bar, pixel-matched to QtWidgets reference at 1920×154. */
Item {
    id: root
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Bar"
    Accessible.description: qsTr("Barra de reproducción con controles de play/pause, siguiente, anterior, volumen y seek")
    objectName: "nowPlayingBar"
    focus: true

    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var outputBridge: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property string densityMode: "full"
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _backendAvailable: root.ps ? root.ps.backendAvailable : false
    property string _lastShownError: ""
    readonly property bool compactLayout: densityMode === "compact"
    readonly property bool mediumLayout: densityMode === "reduced"

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

    function bridgeValue(name, fallbackValue) {
        if (!root.ps) return fallbackValue
        var value = root.ps[name]
        return typeof value === "undefined" ? fallbackValue : value
    }
    function openTrackContext() {
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate(root._hasTrack ? "nowplaying" : "library")
    }
    function formatTime(sec) {
        if (isNaN(sec) || sec < 0) return "--:--"
        var m = Math.floor(sec / 60)
        var s = Math.floor(sec % 60)
        if (m >= 60) {
            var h = Math.floor(m / 60)
            m = m % 60
            return h + ":" + (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s
        }
        return m + ":" + (s < 10 ? "0" : "") + s
    }

    implicitHeight: compactLayout ? 72 : 154
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
        color: "#090B11"
        Rectangle {
            anchors.top: parent.top; width: parent.width; height: 1
            color: MichiTheme.colors.nowPlayingBorder
        }
    }

    /* ── Desktop layout (>= 900) ── */
    Item {
        anchors.fill: parent
        anchors { leftMargin: 14; rightMargin: 14; topMargin: 0; bottomMargin: 0 }
        visible: !compactLayout

        /* Metadata Card — x:38, y:34, w:270, h:86, r:16 at 1920 */
        Rectangle {
            id: metadataCard
            x: 24; y: 34; width: 270; height: 86; radius: 16
            color: metadataMouse.containsMouse ? MichiTheme.colors.nowPlayingTransportHover : MichiTheme.colors.surfaceCard
            border { width: 1; color: metadataMouse.containsMouse ? MichiTheme.colors.nowPlayingTransportHoverBorder : MichiTheme.colors.nowPlayingQualityBorder }
            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }

            /* Cover 64×64 */
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
                    Rectangle { width: 5; height: 5; radius: 3; anchors.centerIn: parent
                        color: root.ps && root.ps.isPlaying ? MichiTheme.colors.nowPlayingGradientMiddle : MichiTheme.colors.textMuted }
                }
            }
            /* Title — y:51global → 17 card-relative */
            Text {
                x: 90; y: 17; width: parent.width - 106
                text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                font { pixelSize: 14; weight: Font.DemiBold }
                elide: Text.ElideRight; maximumLineCount: 1
            }
            /* Artist/Album — y:74global → 40 */
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
            /* Source/Format — y:95global → 61 */
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

        /* Timeline Zone */
        Item {
            id: timelineZone
            anchors.left: metadataCard.right; anchors.leftMargin: 32
            anchors.right: volumeUtilityZone.left; anchors.rightMargin: 31
            y: 43; height: 8

            Text {
                id: currentTimeLabel
                anchors.right: rail.left; anchors.rightMargin: 8; y: -16
                text: formatTime(root.ps ? (root.ps.position || 0) / 1000 : 0)
                color: MichiTheme.colors.textSecondary; font.pixelSize: 11
            }
            Rectangle {
                id: rail
                anchors.left: parent.left; anchors.right: parent.right
                y: 0; height: 8; radius: 4
                color: MichiTheme.colors.nowPlayingTrack
                Rectangle {
                    height: parent.height; radius: 4
                    width: root.ps && root.ps.duration > 0 ? (root.ps.position / root.ps.duration) * parent.width : 0
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#FF7A00" }
                        GradientStop { position: 0.5; color: "#FF4F72" }
                        GradientStop { position: 1.0; color: "#C65CFF" }
                    }
                }
                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onPressed: function(mouse) {
                        if (!root.ps || !root.ps.seekSupported) return
                        var pos = Math.round((mouse.x / width) * (root.ps.duration || 0))
                        root.ps.seek(pos)
                    }
                    onPositionChanged: function(mouse) {
                        if (!pressed || !root.ps) return
                        currentTimeLabel.text = formatTime((mouse.x / width) * (root.ps.duration || 0) / 1000)
                    }
                }
            }
            Rectangle {
                x: root.ps && root.ps.duration > 0 ? rail.x + (root.ps.position / root.ps.duration) * rail.width - 9 : rail.x - 9
                y: -5; width: 18; height: 18; radius: 9
                color: "#FF4F72"; border { width: 2; color: "#FFFFFF" }
                opacity: root._hasTrack ? 1.0 : 0.3
            }
            Text {
                anchors.left: rail.right; anchors.leftMargin: 8; y: -16
                text: formatTime(root.ps ? (root.ps.duration || 0) / 1000 : 0)
                color: MichiTheme.colors.textSecondary; font.pixelSize: 11
            }
        }

        /* Top Right: Volume + EQ + Transmit */
        Item {
            id: volumeUtilityZone
            anchors.right: parent.right; anchors.rightMargin: 48
            y: 28; height: 44; width: 230

            MichiIconButton {
                x: 0; y: 2; width: 40; height: 40; btnSize: 40
                iconKey: "speaker"
                enabled: root._hasTrack && root.ps && root.ps.muteSupported
                Accessible.name: root.ps && root.ps.muted ? qsTr("Activar sonido") : qsTr("Silenciar")
                tooltipText: qsTr("Silenciar")
                onClicked: if (root.ps) root.ps.toggleMute()
            }
            Item {
                x: 48; y: 2; width: 80; height: 40
                Rectangle {
                    y: 16; width: parent.width; height: 8; radius: 4
                    color: MichiTheme.colors.nowPlayingTrack
                    Rectangle {
                        height: parent.height; radius: 4
                        width: root.ps ? (root.ps.volume / 100) * parent.width : 0
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#FF7A00" }
                            GradientStop { position: 1.0; color: "#FF4F72" }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onPressed: function(mouse) { _setVol(mouse.x) }
                        onPositionChanged: function(mouse) { if (pressed) _setVol(mouse.x) }
                        function _setVol(mx) {
                            if (!root.ps) return
                            var vol = Math.max(0, Math.min(100, Math.round((mx / width) * 100)))
                            root.ps.setVolume(vol)
                        }
                    }
                }
            }
            MichiIconButton {
                x: 136; y: 2; width: 40; height: 40; btnSize: 40
                iconKey: "eq"
                enabled: typeof capabilityBridge === "undefined" || !capabilityBridge || capabilityBridge.has("eq")
                Accessible.name: qsTr("Ecualizador"); tooltipText: qsTr("Ecualizador")
                onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("equalizer")
            }
            MichiIconButton {
                x: 184; y: 2; width: 40; height: 40; btnSize: 40
                iconKey: "streaming"
                enabled: root._hasTrack
                Accessible.name: qsTr("Transmitir"); tooltipText: qsTr("Transmitir")
                onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("home_audio")
            }
        }

        /* Lower Center: Transport */
        Item {
            id: transportZone
            anchors.left: metadataCard.right; anchors.leftMargin: 20
            anchors.right: lowerUtilityZone.left; anchors.rightMargin: 9
            y: 88; height: 66

            Item {
                x: Math.round((parent.width - 270) / 2); y: 6; width: 270; height: 54

                MichiIconButton {
                    x: 0; y: 7; width: 40; height: 40; btnSize: 40
                    iconKey: "shuffle"
                    selected: root.ps ? root.ps.shuffleEnabled : false
                    enabled: root._hasTrack && root.ps && root.ps.shuffleSupported && !root.ps.commandPending
                    Accessible.name: qsTr("Aleatorio")
                    onClicked: if (root.ps) root.ps.toggleShuffle()
                }
                MichiIconButton {
                    x: 42; y: 5; width: 44; height: 44; btnSize: 44
                    iconKey: "previous"
                    enabled: root._hasTrack && root.ps && root.ps.previousSupported && !root.ps.commandPending
                    Accessible.name: qsTr("Anterior")
                    onClicked: if (root.ps) root.ps.previous()
                }
                Rectangle {
                    x: 108; y: 0; width: 54; height: 54; radius: 18
                    color: "#1B1D24"; border { width: 1; color: "#2C313D" }
                    MichiIconButton {
                        anchors.centerIn: parent
                        iconKey: root.ps && root.ps.isPlaying ? "pause" : "play"
                        btnSize: 54; width: 54; height: 54
                        enabled: root._hasTrack && !root.ps.commandPending
                        Accessible.name: root.ps && root.ps.isPlaying ? qsTr("Pausar") : qsTr("Reproducir")
                        onClicked: if (root.ps) root.ps.togglePlay()
                    }
                }
                MichiIconButton {
                    x: 184; y: 5; width: 44; height: 44; btnSize: 44
                    iconKey: "next"
                    enabled: root._hasTrack && root.ps && root.ps.nextSupported && !root.ps.commandPending
                    Accessible.name: qsTr("Siguiente")
                    onClicked: if (root.ps) root.ps.next()
                }
                MichiIconButton {
                    x: 230; y: 7; width: 40; height: 40; btnSize: 40
                    iconKey: root.ps && root.ps.repeatMode === "one" ? "repeat_one" : "repeat"
                    selected: root.ps && root.ps.repeatMode !== "none"
                    enabled: root._hasTrack && root.ps && root.ps.repeatSupported && !root.ps.commandPending
                    Accessible.name: root.ps && root.ps.repeatMode === "one" ? qsTr("Repetir una") : qsTr("Repetir")
                    onClicked: if (root.ps) root.ps.toggleRepeat()
                }
            }
        }

        /* Lower Right: Output + Profile buttons */
        Item {
            id: lowerUtilityZone
            anchors.right: parent.right; anchors.rightMargin: 48
            y: 88; width: 260; height: 54

            MichiIconButton {
                x: 52; y: 7; width: 40; height: 40; btnSize: 40
                iconKey: "speaker"
                enabled: root._backendAvailable
                Accessible.name: qsTr("Elegir salida de audio"); tooltipText: qsTr("Elegir salida de audio")
                onClicked: outputPopup.open()
            }
            MichiIconButton {
                x: 106; y: 7; width: 40; height: 40; btnSize: 40
                iconKey: "eq"
                enabled: root.outputBridge !== null
                Accessible.name: qsTr("Elegir perfil de salida"); tooltipText: qsTr("Elegir perfil de salida")
                onClicked: profilePopup.open()
            }
        }

        /* Quality Badge — x:1722, y:86, w:150, h:34 */
        Rectangle {
            x: parent.width - 198; y: 86; width: 150; height: 34; radius: 16
            color: "#1C1814"; border { width: 1; color: "#3D3028" }
            Row {
                anchors.centerIn: parent; spacing: 6
                Rectangle { width: 6; height: 6; radius: 3; anchors.verticalCenter: parent.verticalCenter
                    color: root._hasTrack ? "#FF7A00" : MichiTheme.colors.textMuted }
                Text {
                    text: root._hasTrack ? root.technicalLabel : qsTr("SIN REPRODUCCIÓN")
                    color: "#F4F6FA"
                    font { pixelSize: 11; weight: Font.Medium; letterSpacing: 0.5 }
                }
            }
        }
    }

    /* ── Compact layout ── */
    Item {
        anchors.fill: parent; anchors.margins: 8
        visible: compactLayout

        Rectangle {
            x: 0; y: 12; width: 160; height: 48; radius: 8
            color: MichiTheme.colors.surfaceCard; border { width: 1; color: MichiTheme.colors.nowPlayingQualityBorder }
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
            anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter; compact: true
            isPlaying: root.ps ? root.ps.isPlaying : false; shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
            repeatMode: root.ps ? root.ps.repeatMode : "none"
            commandPending: !root._hasTrack || (root.ps ? root.ps.commandPending : true)
            showPrevious: root._hasTrack && (root.ps ? root.ps.previousSupported : false)
            showNext: root._hasTrack && (root.ps ? root.ps.nextSupported : false)
            onPlayRequested: if (root.ps) root.ps.togglePlay()
            onPauseRequested: if (root.ps) root.ps.togglePlay()
            onPreviousRequested: if (root.ps) root.ps.previous()
            onNextRequested: if (root.ps) root.ps.next()
        }
    }

    OutputProfileMenu {
        id: outputPopup
        x: Math.round(parent.width - width - 48); y: Math.round(-height - 8)
        outputBridge: root.outputBridge
    }
    OutputProfileMenu {
        id: profilePopup
        x: Math.round(parent.width - width - 100); y: Math.round(-height - 8)
        outputBridge: root.outputBridge; showProfiles: true
    }
}
