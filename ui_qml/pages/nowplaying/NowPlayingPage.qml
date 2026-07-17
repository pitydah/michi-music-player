import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root
    objectName: "nowPlayingPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Reproducción"

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge
                   : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _showError: false
    property string _errorText: ""
    readonly property int pageState: {
        if (!root.ps || !root.ps.backendAvailable)
            return root.stateError
        if (root.ps.commandPending && !root.ps.hasTrack)
            return root.stateLoading
        if (!root.ps.hasTrack)
            return root.stateEmpty
        return root.stateReady
    }

    function routeEnter(route) {
        if (root.ps && typeof root.ps.refresh !== "undefined")
            root.ps.refresh()
    }

    LoadingState {
        anchors.centerIn: parent
        visible: root.pageState === root.stateLoading
        title: "Preparando reproducción"
        subtitle: "Sincronizando el estado del motor de audio."
    }

    ErrorState {
        anchors.centerIn: parent
        visible: root.pageState === root.stateError
        title: "Reproductor no disponible"
        message: root.ps && root.ps.errorMessage
                 ? root.ps.errorMessage
                 : "El motor de audio no está disponible en este momento."
        showRetry: root.ps !== null
        onRetryRequested: {
            if (root.ps && typeof root.ps.refresh !== "undefined")
                root.ps.refresh()
        }
    }

    EmptyState {
        anchors.centerIn: parent
        visible: root.pageState === root.stateEmpty
        title: "Sin reproducción activa"
        subtitle: "Selecciona una canción, un álbum, una playlist o una emisora para comenzar."
        iconText: "play"
        showAction: true
        actionText: "Abrir biblioteca"
        onActionClicked: {
            if (root.nav)
                root.nav.navigate("library")
        }
    }

    Flickable {
        visible: root.pageState === root.stateReady
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        contentHeight: contentColumn.height + MichiTheme.spacing.xl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.md

            NowPlayingHeader {
                width: parent.width
                ps: root.ps
                nav: root.nav
            }

            MichiBanner {
                width: parent.width
                visible: root._showError
                message: root._errorText
                kind: "error"
                dismissible: true
                onDismissed: root._showError = false
            }

            GridLayout {
                width: parent.width
                columns: parent.width > 800 ? 2 : 1
                rowSpacing: MichiTheme.spacing.md
                columnSpacing: MichiTheme.spacing.lg

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.sm

                    NowPlayingArtwork {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.min(240, parent.width * 0.55)
                        Layout.preferredHeight: Layout.preferredWidth
                        coverKey: root.ps ? root.ps.coverPath : ""
                        placeholderMode: !root._hasTrack
                    }

                    NowPlayingMetadata {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignHCenter
                        ps: root.ps
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.xs
                        visible: root.ps && root.ps.qualityInfoAvailable

                        StatusBadge { text: root.ps ? root.ps.formatLabel : ""; kind: "info"; visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.sampleRate : ""; kind: "info"; visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.bitDepth : ""; kind: "info"; visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.bitrate : ""; kind: "info"; visible: text !== "" }
                    }

                    StatusBadge {
                        Layout.alignment: Qt.AlignHCenter
                        text: root.ps && root.ps.isPlaying ? "Reproduciendo"
                              : root.ps && root.ps.backendAvailable ? "Pausado" : "No disponible"
                        kind: root.ps && root.ps.isPlaying ? "success"
                              : root.ps && root.ps.backendAvailable ? "info" : "disconnected"
                    }

                    NowPlayingProgress {
                        Layout.fillWidth: true
                        ps: root.ps
                    }

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

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.maximumWidth: 240
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Vol."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }

                        NowPlayingVolume {
                            Layout.fillWidth: true
                            volume: root.ps ? root.ps.volume : 80
                            muted: root.ps ? root.ps.muted : false
                            volumeSupported: root.ps ? root.ps.volumeSupported : false
                            muteSupported: root.ps ? root.ps.muteSupported : false
                            onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                            onMuteClicked: { if (root.ps) root.ps.toggleMute() }
                        }
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.sm
                        visible: root._hasTrack

                        MichiButton {
                            text: "Letra"
                            variant: "ghost"
                            onClicked: { if (root.nav) root.nav.navigate("lyrics") }
                        }
                        MichiButton {
                            text: "Cola"
                            variant: "ghost"
                            onClicked: { if (root.nav) root.nav.navigate("queue") }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: MichiTheme.colors.borderSubtle
                        visible: root._hasTrack
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Información técnica"
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: MichiTheme.typography.weightMedium
                        visible: root._hasTrack
                    }

                    NowPlayingTechnicalInfo {
                        Layout.fillWidth: true
                        ps: root.ps
                        visible: root._hasTrack
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Salida de audio"
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: MichiTheme.typography.weightMedium
                        visible: root._hasTrack
                    }

                    NowPlayingOutputSelector {
                        Layout.fillWidth: true
                        ps: root.ps
                        visible: root._hasTrack
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: parent.width > 700 ? parent.width * 0.35 : parent.width
                    spacing: MichiTheme.spacing.sm

                    NowPlayingQueuePreview {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        ps: root.ps
                        nav: root.nav
                    }

                    NowPlayingLyricsPane {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        ps: root.ps
                    }
                }
            }
        }
    }

    Connections {
        target: root.ps
        function onErrorChanged() {
            if (root.ps && root.ps.errorMessage) {
                root._errorText = root.ps.errorMessage
                root._showError = true
            }
        }
        function onCommandStateChanged() {
            if (root.ps && root.ps.lastCommandError && root.ps.lastCommandMessage) {
                root._errorText = root.ps.lastCommandMessage
                root._showError = true
            } else if (root.ps && root.ps.lastCommandOk) {
                root._showError = false
            }
        }
    }
}
