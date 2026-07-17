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

    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge
                   : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _showError: false
    property string _errorText: ""
    property int pageState: root.ps ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    function routeEnter(route) {
        if (root.ps && typeof root.ps.refresh !== "undefined")
            root.ps.refresh()
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: "Cargando reproducción" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: "Reproducción no disponible" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: "Sin reproducción activa" }
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

            Rectangle {
                width: parent.width
                height: _showError ? 36 : 0
                radius: MichiTheme.radius.sm
                visible: _showError
                color: MichiTheme.colors.error
                clip: true

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.md
                    anchors.rightMargin: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Text {
                        Layout.fillWidth: true
                        text: _errorText
                        color: "white"
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    Text {
                        text: "Cerrar"
                        color: MichiTheme.colors.onError
                        font.pixelSize: MichiTheme.typography.metaSize
                        MouseArea {
                            anchors.fill: parent
                            onClicked: _showError = false
                        }
                    }
                }
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
                        onPlayClicked: { root.ps && root.ps.togglePlay() }
                        onPrevClicked: { root.ps && root.ps.previous() }
                        onNextClicked: { root.ps && root.ps.next() }
                        onShuffleClicked: { root.ps && root.ps.toggleShuffle() }
                        onRepeatClicked: { root.ps && root.ps.toggleRepeat() }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.maximumWidth: 200
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
                            onVolumeAdjusted: function(vol) { root.ps && root.ps.setVolume(vol) }
                            onMuteClicked: { root.ps && root.ps.toggleMute() }
                        }
                    }

                    NowPlayingTechnicalInfo {
                        Layout.fillWidth: true
                        ps: root.ps
                    }

                    NowPlayingOutputSelector {
                        Layout.fillWidth: true
                        ps: root.ps
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.sm
                        visible: root._hasTrack

                        MichiButton { text: "Letra"; variant: "ghost"; onClicked: { root.nav && root.nav.navigate("lyrics") } }
                        MichiButton { text: "Cola"; variant: "ghost"; onClicked: { root.nav && root.nav.navigate("queue") } }
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
                _errorText = root.ps.errorMessage
                _showError = true
            }
        }
        function onCommandStateChanged() {
            if (root.ps && root.ps.lastCommandError && root.ps.lastCommandMessage) {
                _errorText = root.ps.lastCommandMessage
                _showError = true
            } else if (root.ps && root.ps.lastCommandOk) {
                _showError = false
            }
        }
    }
}
