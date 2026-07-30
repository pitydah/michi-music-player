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
    Accessible.description: "Control de reproducción actual: play/pause, siguiente/anterior, volumen, seek y controles de calidad"

    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var qb: typeof queueBridge !== "undefined" ? queueBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _showError: false
    property string _errorText: ""
    property int pageState: !root.ps ? stateError : (root.ps.commandPending ? stateLoading : !root._hasTrack ? stateEmpty : stateReady)
    readonly property bool wideLayout: readyView.width >= 760

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
        sourceComponent: LoadingState { title: qsTr("Cargando reproducción") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState {
            message: qsTr("Reproducción no disponible")
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState {
            title: qsTr("Sin reproducción activa")
            actionText: qsTr("Explorar biblioteca")
            onActionClicked: if (root.nav) root.nav.navigate("library")
        }
    }

    Flickable {
        id: readyView
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
                        color: MichiTheme.colors.textOnError
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    Text {
                        text: qsTr("Cerrar")
                        color: MichiTheme.colors.textOnError
                        font.pixelSize: MichiTheme.typography.metaSize
                        MouseArea {
                            anchors.fill: parent
                            onClicked: _showError = false
                        }
                    }
                }
            }

            GridLayout {
                id: playbackGrid
                width: parent.width
                columns: root.wideLayout ? 2 : 1
                rowSpacing: MichiTheme.spacing.xl
                columnSpacing: MichiTheme.spacing.xl

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: root.wideLayout ? 520 : playbackGrid.width
                    spacing: MichiTheme.spacing.md

                    NowPlayingArtwork {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.min(root.wideLayout ? 280 : 240,
                                                        parent.width * (root.wideLayout ? 0.58 : 0.52))
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

                        StatusBadge { text: root.ps ? root.ps.formatLabel : ""; kind: qsTr("info"); visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.sampleRate : ""; kind: qsTr("info"); visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.bitDepth : ""; kind: qsTr("info"); visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.bitrate : ""; kind: qsTr("info"); visible: text !== "" }
                    }

                    StatusBadge {
                        Layout.alignment: Qt.AlignHCenter
                        text: !root.ps || !root._hasTrack ? "Sin reproducción"
                            : root.ps.isPlaying ? "Reproduciendo" : "Pausado"
                        kind: !root.ps || !root._hasTrack ? "disconnected"
                            : root.ps.isPlaying ? "success" : "info"
                    }

                    PlaybackProgress {
                        Layout.fillWidth: true
                        position: root.ps ? root.ps.position : 0
                        duration: root.ps ? root.ps.duration : 0
                        seekable: root.ps ? root.ps.seekSupported : false
                        onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: parent.width >= 500 ? 2 : 1
                        rowSpacing: MichiTheme.spacing.sm
                        columnSpacing: MichiTheme.spacing.lg

                        PlaybackTransport {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 230
                            isPlaying: root.ps ? root.ps.isPlaying : false
                            shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                            repeatMode: root.ps ? root.ps.repeatMode : "none"
                            commandPending: !root._hasTrack
                                            || (root.ps ? root.ps.commandPending || !root.ps.playPauseSupported : true)
                            showPrevious: root.ps ? root.ps.previousSupported : false
                            showNext: root.ps ? root.ps.nextSupported : false
                            showShuffle: root.ps ? root.ps.shuffleSupported : false
                            showRepeat: root.ps ? root.ps.repeatSupported : false
                            onPlayRequested: { root.ps && root.ps.togglePlay() }
                            onPauseRequested: { root.ps && root.ps.togglePlay() }
                            onPreviousRequested: { root.ps && root.ps.previous() }
                            onNextRequested: { root.ps && root.ps.next() }
                            onShuffleToggled: { root.ps && root.ps.toggleShuffle() }
                            onRepeatCycled: { root.ps && root.ps.toggleRepeat() }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.maximumWidth: 220
                            Layout.alignment: Qt.AlignHCenter
                            spacing: MichiTheme.spacing.sm

                            Text {
                                text: qsTr("Vol.")
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
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.sm
                        visible: root._hasTrack

                        MichiButton { text: qsTr("Letra"); variant: "ghost"; onClicked: { root.nav && root.nav.navigate("lyrics") } }
                        MichiButton { text: qsTr("Cola"); variant: "ghost"; onClicked: { root.nav && root.nav.navigate("queue") } }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: root.wideLayout ? 340 : playbackGrid.width
                    spacing: MichiTheme.spacing.md

                    NowPlayingQueuePreview {
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.wideLayout ? 260 : 220
                        qb: root.qb
                        nav: root.nav
                    }

                    NowPlayingLyricsPane {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        ps: root.ps
                    }
                }
            }

            GridLayout {
                width: parent.width
                columns: width >= 680 ? 2 : 1
                rowSpacing: MichiTheme.spacing.lg
                columnSpacing: MichiTheme.spacing.xl
                visible: root._hasTrack

                NowPlayingTechnicalInfo {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    ps: root.ps
                }

                NowPlayingOutputSelector {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    ps: root.ps
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
            if (root.ps && root.ps.commandState === "confirmed") {
                _showError = false
            }
        }
    }
}
