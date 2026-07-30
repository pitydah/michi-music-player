import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"

/* NowPlayingBar — canonical playback bar, pixel-matched to QtWidgets reference at 1920×154.
 *
 * Geometry:
 *   Bar: 154px tall
 *   Top row center: y:50
 *   Bottom row center: y:104
 *   Metadata card spans both rows, center at y:77
 */
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

    /* ── Desktop layout (>= 900) — 154px, top row y:50, bottom row y:104 ── */
    Item {
        anchors.fill: parent
        anchors.leftMargin: 14
        visible: !compactLayout

        /* Metadata Card — spans both rows, center at bar center y:77 */
        Rectangle {
            id: metadataCard
            x: 24; y: 34; width: 270; height: 86; radius: 16
            color: metadataMouse.containsMouse ? MichiTheme.colors.nowPlayingTransportHover : MichiTheme.colors.surfaceCard
            border { width: 1; color: metadataMouse.containsMouse ? MichiTheme.colors.nowPlayingTransportHoverBorder : MichiTheme.colors.nowPlayingQualityBorder }
            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }

            /* Cover 64×64 at offset 12,11 from card */
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
            /* Title */
            Text {
                x: 90; y: 17; width: parent.width - 106
                text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                font { pixelSize: 14; weight: Font.DemiBold }
                elide: Text.ElideRight; maximumLineCount: 1
            }
            /* Artist/Album */
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
            /* Source/Format */
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
            activeFocusOnTab: true
            Keys.onSpacePressed: root.openTrackContext()
            Keys.onReturnPressed: root.openTrackContext()
        }

        /* ── TOP ROW (center y:50) ── */

        /* Timeline — dominates the top row */
        Item {
            id: timelineZone
            anchors.left: metadataCard.right; anchors.leftMargin: 32
            anchors.right: topUtilityZone.left; anchors.rightMargin: 31
            y: 46; height: 8

            Text {
                id: timeCurrent
                anchors.right: rail.left; anchors.rightMargin: 8
                y: -17
                text: formatTime(root.ps ? (root.ps.position || 0) / 1000 : 0)
                color: MichiTheme.colors.textSecondary; font.pixelSize: 11
            }
            Rectangle {
                id: rail
                anchors.left: parent.left; anchors.right: parent.right
                height: 8; radius: 4
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
                        timeCurrent.text = formatTime((mouse.x / width) * (root.ps.duration || 0) / 1000)
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
                anchors.left: rail.right; anchors.leftMargin: 8; y: -17
                text: formatTime(root.ps ? (root.ps.duration || 0) / 1000 : 0)
                color: MichiTheme.colors.textSecondary; font.pixelSize: 11
            }
        }

        /* Top Right: Volume slider + EQ + Transmit — centered at y:50 */
        Item {
            id: topUtilityZone
            anchors.right: parent.right; anchors.rightMargin: 48
            y: 28; height: 44; width: 224

            MichiIconButton {
                x: 0; y: 2; width: 40; height: 40; btnSize: 40
                symbolicColor: "#FFFFFF"
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
                symbolicColor: "#FFFFFF"
                iconKey: "eq"
                enabled: typeof capabilityBridge === "undefined" || !capabilityBridge || capabilityBridge.has("eq")
                Accessible.name: qsTr("Ecualizador"); tooltipText: qsTr("Ecualizador")
                onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("equalizer")
            }
            MichiIconButton {
                x: 184; y: 2; width: 40; height: 40; btnSize: 40
                symbolicColor: "#FFFFFF"
                iconKey: "streaming"
                enabled: root._hasTrack
                Accessible.name: qsTr("Transmitir"); tooltipText: qsTr("Transmitir")
                onClicked: if (typeof navigationBridge !== "undefined") navigationBridge.navigate("home_audio")
            }
        }

        /* ── BOTTOM ROW (center y:104) ── */

        /* Transport — centered in its zone, not the whole window */
        Item {
            id: transportZone
            anchors.left: metadataCard.right; anchors.leftMargin: 20
            anchors.right: lowerUtilityZone.left; anchors.rightMargin: 9
            y: 77; height: 54

            Item {
                anchors.centerIn: parent
                width: 270; height: 54

                /* Shuffle — 40×40 */
                MichiIconButton {
                    x: 0; y: 7; width: 40; height: 40; btnSize: 40
                symbolicColor: "#FFFFFF"
                    iconKey: "shuffle"
                    selected: root.ps ? root.ps.shuffleEnabled : false
                    enabled: root._hasTrack && root.ps && root.ps.shuffleSupported && !root.ps.commandPending
                    Accessible.name: qsTr("Aleatorio")
                    onClicked: if (root.ps) root.ps.toggleShuffle()
                }
                /* Previous — 44×44 */
                MichiIconButton {
                    x: 52; y: 5; width: 44; height: 44; btnSize: 44
                symbolicColor: "#FFFFFF"
                    iconKey: "previous"
                    enabled: root._hasTrack && root.ps && root.ps.previousSupported && !root.ps.commandPending
                    Accessible.name: qsTr("Anterior")
                    onClicked: if (root.ps) root.ps.previous()
                }
                /* Play/Pause — 54×54, centerpiece */
                Rectangle {
                    x: 108; y: 0; width: 54; height: 54; radius: 18
                    color: "#1B1D24"; border { width: 1; color: "#2C313D" }
                    MichiIconButton {
                        anchors.centerIn: parent
                        iconKey: root.ps && root.ps.isPlaying ? "pause" : "play"
                        btnSize: 54; width: 54; height: 54
                symbolicColor: "#FFFFFF"
                        enabled: root._hasTrack && !root.ps.commandPending
                        Accessible.name: root.ps && root.ps.isPlaying ? qsTr("Pausar") : qsTr("Reproducir")
                        onClicked: if (root.ps) root.ps.togglePlay()
                    }
                }
                /* Next — 44×44 */
                MichiIconButton {
                    x: 174; y: 5; width: 44; height: 44; btnSize: 44
                symbolicColor: "#FFFFFF"
                    iconKey: "next"
                    enabled: root._hasTrack && root.ps && root.ps.nextSupported && !root.ps.commandPending
                    Accessible.name: qsTr("Siguiente")
                    onClicked: if (root.ps) root.ps.next()
                }
                /* Repeat — 40×40 */
                MichiIconButton {
                    x: 230; y: 7; width: 40; height: 40; btnSize: 40
                symbolicColor: "#FFFFFF"
                    iconKey: root.ps && root.ps.repeatMode === "one" ? "repeat_one" : "repeat"
                    selected: root.ps && root.ps.repeatMode !== "none"
                    enabled: root._hasTrack && root.ps && root.ps.repeatSupported && !root.ps.commandPending
                    Accessible.name: root.ps && root.ps.repeatMode === "one" ? qsTr("Repetir una") : qsTr("Repetir")
                    onClicked: if (root.ps) root.ps.toggleRepeat()
                }
            }
        }

        /* Lower Right: Output + Profile + Badge — centered at y:104 */
        Item {
            id: lowerUtilityZone
            anchors.right: parent.right; anchors.rightMargin: 48
            y: 77; height: 54; width: 340

            /* Audio Output */
            MichiIconButton {
                x: 0; y: 7; width: 40; height: 40; btnSize: 40
                symbolicColor: "#FFFFFF"
                iconKey: "speaker"
                enabled: root._backendAvailable
                Accessible.name: qsTr("Elegir salida de audio"); tooltipText: qsTr("Elegir salida de audio")
                onClicked: {
                    if (typeof audioOutputBridge !== "undefined" && audioOutputBridge)
                        outputPopup.open()
                    else if (typeof navigationBridge !== "undefined")
                        navigationBridge.navigate("outputs")
                }
            }
            /* Output Profile */
            MichiIconButton {
                x: 48; y: 7; width: 40; height: 40; btnSize: 40
                symbolicColor: "#FFFFFF"
                iconKey: "eq"
                enabled: root.outputBridge !== null
                Accessible.name: qsTr("Elegir perfil de salida"); tooltipText: qsTr("Elegir perfil de salida")
                onClicked: profilePopup.open()
            }
            /* Quality Badge — right-aligned */
            Rectangle {
                anchors.right: parent.right; y: 10
                width: Math.min(150, parent.width - 100)
                height: 34; radius: 16
                color: "#1C1814"; border { width: 1; color: "#3D3028" }
                Row {
                    anchors.centerIn: parent; spacing: 6
                    Rectangle { width: 6; height: 6; radius: 3; anchors.verticalCenter: parent.verticalCenter
                        color: root._hasTrack ? "#FF7A00" : MichiTheme.colors.textMuted }
                    Text {
                        text: root._hasTrack ? root.technicalLabel : qsTr("SIN REPRODUCCIÓN")
                        color: "#F4F6FA"
                        font { pixelSize: 11; weight: Font.Medium; letterSpacing: 0.5 }
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    /* ── Compact layout (72px) ── */
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

    AudioOutputMenu {
        id: outputPopup
        x: parent.width - width - 48; y: -height - 8
        outputBridge: root.outputBridge
    }
    OutputProfileMenu {
        id: profilePopup
        x: parent.width - width - 100; y: -height - 8
        outputBridge: root.outputBridge
    }
}
