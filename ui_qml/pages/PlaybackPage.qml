import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: root
    objectName: "playbackPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Reproducción detallada"

    property var ps: typeof playbackBridge !== "undefined" ? playbackBridge
                   : (typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null)
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var act: typeof actionRegistry !== "undefined" ? actionRegistry : null
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
        sourceComponent: LoadingState { title: qsTr("Cargando reproducción") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: qsTr("Servicio de reproducción no disponible") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: qsTr("Sin reproducción activa") }
    }

    Flickable {
        visible: root.pageState === root.stateReady
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: grid.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        GridLayout {
            id: grid
            width: parent.width
            columns: parent.width > 900 ? 2 : 1
            columnSpacing: MichiTheme.spacing.xl
            rowSpacing: MichiTheme.spacing.lg

            // ── Columna izquierda: Portada + info + controles ──
            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.md

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: Math.min(280, parent.width * 0.6)
                    Layout.preferredHeight: Layout.preferredWidth
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceCard
                    visible: root._hasTrack

                    Image {
                        anchors.fill: parent
                        source: root.ps && root.ps.coverUrl ? root.ps.coverUrl : ""
                        fillMode: Image.PreserveAspectCrop
                        sourceSize.width: 280
                        sourceSize.height: 280
                    }

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("♫")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: 48
                        visible: parent.source === "" || parent.status === Image.Error
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    Layout.maximumWidth: 400
                    text: root._hasTrack && root.ps ? root.ps.trackTitle : qsTr("Sin reproducción")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    Layout.maximumWidth: 400
                    text: root.ps && root.ps.trackArtist ? root.ps.trackArtist : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    visible: text !== ""
                }

                Text {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    Layout.maximumWidth: 400
                    text: root.ps && root.ps.trackAlbum ? root.ps.trackAlbum : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    visible: text !== ""
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

                NowPlayingSeekBar {
                    Layout.fillWidth: true
                    Layout.maximumWidth: 400
                    Layout.alignment: Qt.AlignHCenter
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    enabled: root.ps ? root.ps.seekSupported : false
                    onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                }

                NowPlayingControls {
                    Layout.alignment: Qt.AlignHCenter
                    isPlaying: root.ps ? root.ps.isPlaying : false
                    shuffleEnabled: root.ps ? root.ps.shuffleEnabled : false
                    repeatMode: root.ps ? root.ps.repeatMode : "none"
                    onPlayClicked: { if (root.ps) root.ps.togglePlay() }
                    onPrevClicked: { if (root.ps) root.ps.previous() }
                    onNextClicked: { if (root.ps) root.ps.next() }
                    onShuffleClicked: { if (root.ps) root.ps.toggleShuffle() }
                    onRepeatClicked: { if (root.ps) root.ps.toggleRepeat() }
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.maximumWidth: 300
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
                        onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                        onMuteClicked: { if (root.ps) root.ps.toggleMute() }
                    }
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: MichiTheme.spacing.sm
                    visible: root._hasTrack

                    MichiButton { text: qsTr("Letra"); variant: "ghost"; onClicked: { if (root.nav) root.nav.navigate("lyrics") } }
                    MichiButton { text: qsTr("Metadata"); variant: "ghost"; onClicked: { if (root.nav) root.nav.navigate("metadata_inspector") } }
                }
            }

            // ── Columna derecha: Cola + Historial ──
            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.md
                visible: root._hasTrack

                Text {
                    text: qsTr("Cola de reproducción")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(200, (root.ps ? root.ps.queue.length : 0) * 32 + 10)
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceCard
                    border.width: 1
                    border.color: MichiTheme.colors.borderCard

                    ListView {
                        id: queueView
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        model: root.ps ? root.ps.queue : []
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        focusPolicy: Qt.StrongFocus

                        delegate: Row {
                            width: queueView.width; height: 28; spacing: MichiTheme.spacing.sm
                            Text {
                                text: modelData.title || "—"
                                color: modelData.is_current ? MichiTheme.colors.accent : MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.secondarySize
                                elide: Text.ElideRight; width: parent.width * 0.55
                            }
                            Text {
                                text: modelData.artist || ""
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.secondarySize
                                elide: Text.ElideRight; width: parent.width * 0.4
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: root.ps && root.ps.queue.length === 0 ? "Cola vacía" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            visible: text !== ""
                        }
                    }
                }

                Text {
                    text: qsTr("Historial reciente")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    visible: root.ps && root.ps.history && root.ps.history.length > 0
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(150, (root.ps ? Math.min(root.ps.history.length, 10) : 0) * 28 + 10)
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceCard
                    border.width: 1
                    border.color: MichiTheme.colors.borderCard
                    visible: root.ps && root.ps.history && root.ps.history.length > 0

                    ListView {
                        id: historyView
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        model: root.ps ? root.ps.history.slice(0, 10) : []
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: Row {
                            width: historyView.width; height: 28; spacing: MichiTheme.spacing.sm
                            Text {
                                text: modelData.title || "—"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.secondarySize
                                elide: Text.ElideRight; width: parent.width * 0.55
                            }
                            Text {
                                text: modelData.artist || ""
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.secondarySize
                                elide: Text.ElideRight; width: parent.width * 0.4
                            }
                        }
                    }
                }

                Text {
                    text: root.ps && root.ps.history && root.ps.history.length > 0
                          ? root.ps.history.length + " canciones en el historial"
                          : "Sin historial"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }
    }

    Connections {
        target: root.ps
        onErrorChanged: function() {
            if (root.ps && root.ps.errorMessage) {
                _errorText = root.ps.errorMessage
                _showError = true
            }
        }
        onCommandStateChanged: function() {
            if (root.ps && root.ps.lastCommandError && root.ps.lastCommandMessage) {
                _errorText = root.ps.lastCommandMessage
                _showError = true
            } else if (root.ps && root.ps.lastCommandOk) {
                _showError = false
            }
        }
    }
}
