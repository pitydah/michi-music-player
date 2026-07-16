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

    function routeEnter(route) {
        if (root.ps && typeof root.ps.refresh !== "undefined")
            root.ps.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            // Error banner
            Rectangle {
                width: parent.width
                height: _showError ? 36 : 0
                radius: MichiTheme.radiusSm
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

            // Main content
            GridLayout {
                width: parent.width
                columns: parent.width > 800 ? 2 : 1
                rowSpacing: MichiTheme.spacing.lg
                columnSpacing: MichiTheme.spacing.xl

                // Left column: cover + info + controls
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.md

                    // Cover
                    NowPlayingCover {
                        id: coverArt
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.min(200, parent.width * 0.5)
                        Layout.preferredHeight: Layout.preferredWidth
                        coverKey: root.ps ? root.ps.coverPath : ""
                        placeholderMode: !root._hasTrack
                    }

                    // Title, artist, album
                    Text {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignHCenter
                        text: root._hasTrack && root.ps ? root.ps.trackTitle : "Sin reproducción"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignHCenter
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
                        text: root.ps && root.ps.trackAlbum ? root.ps.trackAlbum : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        visible: text !== ""
                    }

                    // Quality badges
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.xs
                        visible: root.ps && root.ps.qualityInfoAvailable

                        StatusBadge { text: root.ps ? root.ps.formatLabel : ""; kind: "info"; visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.sampleRate : ""; kind: "info"; visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.bitDepth : ""; kind: "info"; visible: text !== "" }
                        StatusBadge { text: root.ps ? root.ps.bitrate : ""; kind: "info"; visible: text !== "" }
                    }

                    // State
                    StatusBadge {
                        Layout.alignment: Qt.AlignHCenter
                        text: root.ps && root.ps.isPlaying ? "Reproduciendo" : root.ps && root.ps.backendAvailable ? "Pausado" : "No disponible"
                        kind: root.ps && root.ps.isPlaying ? "success" : root.ps && root.ps.backendAvailable ? "info" : "disconnected"
                    }

                    // Controls
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

                    // Seek bar
                    NowPlayingSeekBar {
                        Layout.fillWidth: true
                        position: root.ps ? root.ps.position : 0
                        duration: root.ps ? root.ps.duration : 0
                        enabled: root.ps ? root.ps.seekSupported : false
                        onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
                    }

                    // Volume
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
                            onVolumeAdjusted: function(vol) { if (root.ps) root.ps.setVolume(vol) }
                            onMuteClicked: { if (root.ps) root.ps.toggleMute() }
                        }
                    }

                    // Navigation links
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.sm
                        visible: root._hasTrack

                        MichiButton { text: "Letra"; variant: "ghost"; onClicked: { if (root.nav) root.nav.navigate("lyrics") } }
                        MichiButton { text: "Metadata"; variant: "ghost"; onClicked: { if (root.nav) root.nav.navigate("metadata_inspector") } }
                    }
                }

                // Right column: queue + history
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: parent.width > 700 ? parent.width * 0.35 : parent.width
                    spacing: MichiTheme.spacing.md
                    visible: true

                    // Queue
                    Text {
                        text: "Cola"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Item {
                        Layout.fillWidth: true
                        height: Math.min(200, (root.ps ? root.ps.queue.length : 0) * 28 + 10)

                        ListView {
                            focusPolicy: Qt.StrongFocus
                            id: queueView
                            anchors.fill: parent
                            model: root.ps ? root.ps.queue : []
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds

                            delegate: Row {
                                width: queueView.width; height: 24; spacing: MichiTheme.spacing.sm
                                Text {
                                    text: modelData.title || "—"
                                    color: modelData.is_current ? MichiTheme.colors.accent : MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight; width: parent.width * 0.6
                                }
                                Text {
                                    text: modelData.artist || ""
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight; width: parent.width * 0.35
                                }
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

                    // History
                    Text {
                        text: "Historial"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        visible: root.ps && root.ps.history && root.ps.history.length > 0
                    }

                    Item {
                        Layout.fillWidth: true
                        height: Math.min(150, (root.ps ? root.ps.history.length : 0) * 24 + 10)
                        visible: root.ps && root.ps.history && root.ps.history.length > 0

                        ListView {
                            focusPolicy: Qt.StrongFocus
                            anchors.fill: parent
                            model: root.ps ? root.ps.history.slice(0, 10) : []
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds

                            delegate: Row {
                                width: parent.width; height: 24; spacing: MichiTheme.spacing.sm
                                Text {
                                    text: modelData.title || "—"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight; width: parent.width * 0.6
                                }
                                Text {
                                    text: modelData.artist || ""
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight; width: parent.width * 0.3
                                }
                            }
                        }
                    }

                    Text {
                        text: root.ps && root.ps.history && root.ps.history.length > 0
                              ? root.ps.history.length + " canciones"
                              : "Sin historial"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }
            }
        }
    }

    // Track errors via Connections
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
