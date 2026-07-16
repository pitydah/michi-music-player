import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../materials"
import "../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Expanded Now Playing"
    objectName: "expandedNowPlayingPanel"
    focus: true
    id: root

    property var ps: typeof nowplayingBridge !== "undefined" && nowplayingBridge
                     ? nowplayingBridge
                     : (typeof playbackBridge !== "undefined" ? playbackBridge : null)
    property bool expanded: false
    property bool _canPlay: root.ps ? root.ps.backendAvailable : false
    property bool _hasTrack: root.ps ? root.ps.hasTrack : false

    signal closePanel()

    height: expanded ? 280 : 0
    clip: true

    Behavior on height { NumberAnimation { duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic } }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceCardElevated
        radius: MichiTheme.radiusMd

        Rectangle {
            anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter
            width: 40; height: 3; radius: 2
            color: MichiTheme.colors.textMuted; opacity: 0.3
        }

        Flickable {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg
            contentHeight: contentColumn.height; clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: contentColumn; width: parent.width; spacing: MichiTheme.spacing.md

                Row {
                    width: parent.width; spacing: MichiTheme.spacing.lg

                    NowPlayingCover {
                        coverSize: 100
                        coverKey: root.ps ? root.ps.coverPath : ""
                        placeholderMode: !root._hasTrack
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter; spacing: MichiTheme.spacing.xs
                        width: parent.width - 116

                        Text {
                            text: root._hasTrack && root.ps ? root.ps.trackTitle : "Sin reproducción"
                            color: root._hasTrack ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold; elide: Text.ElideRight; width: parent.width
                        }

                        Text {
                            text: root._hasTrack && root.ps ? root.ps.trackArtist : "Selecciona una canción"
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight; width: parent.width; visible: text !== ""
                        }

                        Text {
                            text: root._hasTrack && root.ps ? root.ps.trackAlbum : ""
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; width: parent.width; visible: text !== ""
                        }
                    }
                }

                NowPlayingSeekBar {
                    width: parent.width; anchors.horizontalCenter: parent.horizontalCenter
                    position: root.ps ? root.ps.position : 0
                    duration: root.ps ? root.ps.duration : 0
                    enabled: root._canPlay && root._hasTrack && (root.ps ? root.ps.duration > 0 : false)
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter; spacing: MichiTheme.spacing.sm

                    MichiIconButton {
                        iconSource: "../../icons/nowplaying_clean/warm_shuffle_32.png"
                        iconText: "S"; tooltipText: "Aleatorio"
                        selected: root.ps ? root.ps.shuffleEnabled : false
                        btnSize: 36; enabled: root._canPlay
                        onClicked: { if (root.ps) root.ps.toggleShuffle() }
                    }

                    MichiIconButton {
                        iconSource: "../../icons/nowplaying_clean/warm_prev_32.png"
                        iconText: "<<"; tooltipText: "Anterior"
                        btnSize: 36; enabled: root._canPlay
                        onClicked: { if (root.ps) root.ps.previous() }
                    }

                    Rectangle {
                        width: 48; height: 48; radius: MichiTheme.radiusPill
                        color: root._canPlay && maP.containsMouse ? MichiTheme.colors.surfacePressed : root._canPlay ? MichiTheme.colors.accentBlue : MichiTheme.colors.accentSurface
                        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
                        Image {
                            anchors.centerIn: parent; width: 22; height: 22
                            source: root.ps && root.ps.isPlaying ? "../../icons/nowplaying_clean/warm_pause_32.png" : "../../icons/nowplaying_clean/warm_play_32.png"
                            sourceSize.width: 32; sourceSize.height: 32; fillMode: Image.PreserveAspectFit
                        }
                        MouseArea {
                            id: maP; anchors.fill: parent
                            hoverEnabled: root._canPlay; cursorShape: root._canPlay ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: { if (root._canPlay && root.ps) root.ps.togglePlay() }
                        }
                    }

                    MichiIconButton {
                        iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
                        iconText: ">>"; tooltipText: "Siguiente"
                        btnSize: 36; enabled: root._canPlay
                        onClicked: { if (root.ps) root.ps.next() }
                    }

                    MichiIconButton {
                        iconSource: "../../icons/nowplaying_clean/warm_repeat_32.png"
                        iconText: root.ps && root.ps.repeatMode === "one" ? "1" : "R"
                        tooltipText: "Repetir"
                        selected: root.ps ? root.ps.repeatMode !== "none" : false
                        btnSize: 36; enabled: root._canPlay
                        onClicked: { if (root.ps) root.ps.toggleRepeat() }
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.md; width: parent.width
                    Text { text: root.ps && root.ps.qualityLabel ? root.ps.qualityLabel : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; visible: text !== "" }
                    Text { text: root.ps && root.ps.sourceType ? root.ps.sourceType : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; visible: text !== "" }
                    Item { width: 1; height: 1; Layout.fillWidth: true }
                    StatusBadge {
                        text: !root._canPlay ? "Safe mode" : root.ps && root.ps.playbackStatus === "error" ? "Error" : ""
                        kind: !root._canPlay ? "experimental" : "error"
                        visible: !root._canPlay || (root.ps && root.ps.playbackStatus === "error")
                    }
                }

                NowPlayingQueuePanel {
                    width: parent.width
                    playbackState: root.ps
                    expanded: true
                }

                Text {
                    text: root.ps && root.ps.errorMessage ? root.ps.errorMessage : ""
                    color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }
            }
        }

        MouseArea {
            anchors.top: parent.top; width: parent.width; height: 30
            cursorShape: Qt.PointingHandCursor
            onClicked: root.closePanel()
        }
    }
}
