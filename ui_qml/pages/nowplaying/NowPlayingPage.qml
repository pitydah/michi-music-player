import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    property var ps: typeof nowplayingBridge !== "undefined" ? nowplayingBridge
                   : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false
    property bool _showError: false
    property string _errorText: ""

    objectName: "nowplaying.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Reproducción actual"
    Accessible.description: "Panel de reproducción actual"

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

            NowPlayingHeader {
                width: parent.width
                ps: root.ps
                nav: root.nav
            }

            Rectangle {
                id: errorBanner
                width: parent.width
                height: _showError ? 36 : 0
                radius: MichiTheme.radiusSm
                visible: _showError
                color: MichiTheme.colors.error
                clip: true
                objectName: "nowplaying.errorBanner"

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
                        objectName: "nowplaying.errorText"
                        Accessible.name: _errorText
                    }

                    Text {
                        text: "Cerrar"
                        color: MichiTheme.colors.onError
                        font.pixelSize: MichiTheme.typography.metaSize
                        objectName: "nowplaying.errorClose"
                        Accessible.role: Accessible.Button
                        Accessible.name: "Cerrar mensaje de error"
                        Keys.onReturnPressed: _showError = false
                        Keys.onSpacePressed: _showError = false
                        MouseArea {
                            anchors.fill: parent
                            onClicked: _showError = false
                        }
                    }
                }
            }

            GridLayout {
                id: mainGrid
                width: parent.width
                columns: parent.width > 800 ? 2 : 1
                rowSpacing: MichiTheme.spacing.lg
                columnSpacing: MichiTheme.spacing.xl
                objectName: "nowplaying.mainGrid"

                ColumnLayout {
                    id: leftColumn
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.md
                    objectName: "nowplaying.leftColumn"

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
                        id: qualityRow
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.xs
                        visible: root.ps && root.ps.qualityInfoAvailable
                        objectName: "nowplaying.qualityRow"

                        StatusBadge { id: formatBadge; text: root.ps ? root.ps.formatLabel : ""; kind: "info"; visible: text !== ""; objectName: "nowplaying.badge.format" }
                        StatusBadge { id: sampleBadge; text: root.ps ? root.ps.sampleRate : ""; kind: "info"; visible: text !== ""; objectName: "nowplaying.badge.sampleRate" }
                        StatusBadge { id: depthBadge; text: root.ps ? root.ps.bitDepth : ""; kind: "info"; visible: text !== ""; objectName: "nowplaying.badge.bitDepth" }
                        StatusBadge { id: bitrateBadge; text: root.ps ? root.ps.bitrate : ""; kind: "info"; visible: text !== ""; objectName: "nowplaying.badge.bitrate" }
                    }

                    StatusBadge {
                        id: stateBadge
                        Layout.alignment: Qt.AlignHCenter
                        text: root.ps && root.ps.isPlaying ? "Reproduciendo"
                            : root.ps && root.ps.backendAvailable ? "Pausado" : "No disponible"
                        kind: root.ps && root.ps.isPlaying ? "success"
                            : root.ps && root.ps.backendAvailable ? "info" : "disconnected"
                        objectName: "nowplaying.stateBadge"
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

                    NowPlayingTechnicalInfo {
                        Layout.fillWidth: true
                        ps: root.ps
                    }

                    NowPlayingOutputSelector {
                        Layout.fillWidth: true
                        ps: root.ps
                    }

                    RowLayout {
                        id: navLinksRow
                        Layout.alignment: Qt.AlignHCenter
                        spacing: MichiTheme.spacing.sm
                        visible: root._hasTrack
                        objectName: "nowplaying.navLinks"

                        MichiButton { id: lyricsBtn; text: "Letra"; variant: "ghost"; objectName: "nowplaying.nav.lyrics"; Accessible.name: "Ir a letras"; onClicked: { if (root.nav) root.nav.navigate("lyrics") } }
                        MichiButton { id: queueBtn; text: "Cola"; variant: "ghost"; objectName: "nowplaying.nav.queue"; Accessible.name: "Ir a cola"; onClicked: { if (root.nav) root.nav.navigate("queue") } }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: parent.width > 700 ? parent.width * 0.35 : parent.width
                    spacing: MichiTheme.spacing.md

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
