import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Controls"
    objectName: "nowPlayingControls"
    focus: true
    id: root

    property bool isPlaying: false
    property bool shuffleEnabled: false
    property string repeatMode: "none"
    property bool playPauseSupported: true
    property bool previousSupported: true
    property bool nextSupported: true
    property bool shuffleSupported: true
    property bool repeatSupported: true

    signal playClicked()
    signal prevClicked()
    signal nextClicked()
    signal shuffleClicked()
    signal repeatClicked()

    implicitHeight: 40

    Row {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.xs

        MichiIconButton {
            iconSource: "../../icons/nowplaying_clean/warm_shuffle_32.png"
            iconText: ""
            tooltipText: root.shuffleSupported ? "Aleatorio" : "No soportado por el backend actual"
            selected: root.shuffleEnabled
            btnSize: 34
            enabled: root.shuffleSupported
            opacity: root.shuffleSupported ? 1.0 : 0.35
            onClicked: { if (root.shuffleSupported) root.shuffleClicked() }
        }

        MichiIconButton {
            iconSource: "../../icons/nowplaying_clean/warm_prev_32.png"
            iconText: ""
            tooltipText: root.previousSupported ? "Anterior" : "No soportado por el backend actual"
            btnSize: 34
            enabled: root.previousSupported
            opacity: root.previousSupported ? 1.0 : 0.35
            onClicked: { if (root.previousSupported) root.prevClicked() }
        }

        Item {
            width: 44
            height: 44

            Rectangle {
                anchors.fill: parent
                radius: MichiTheme.radiusPill
                color: root.playPauseSupported && maPlay.containsMouse
                       ? MichiTheme.colors.accentBlue
                       : root.playPauseSupported
                         ? MichiTheme.colors.accentBlue
                         : Qt.rgba(0.561, 0.718, 1.0, 0.25)
                opacity: root.playPauseSupported ? 1.0 : 0.35
                Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

                Image {
                    anchors.centerIn: parent
                    width: 20
                    height: 20
                    source: root.isPlaying
                            ? "../../icons/nowplaying_clean/warm_pause_32.png"
                            : "../../icons/nowplaying_clean/warm_play_32.png"
                    sourceSize.width: 32
                    sourceSize.height: 32
                    fillMode: Image.PreserveAspectFit
                }
            }

            MouseArea {
                id: maPlay
                anchors.fill: parent
                hoverEnabled: root.playPauseSupported
                cursorShape: root.playPauseSupported ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: { if (root.playPauseSupported) root.playClicked() }
            }
        }

        MichiIconButton {
            iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
            iconText: ""
            tooltipText: root.nextSupported ? "Siguiente" : "No soportado por el backend actual"
            btnSize: 34
            enabled: root.nextSupported
            opacity: root.nextSupported ? 1.0 : 0.35
            onClicked: { if (root.nextSupported) root.nextClicked() }
        }

        MichiIconButton {
            iconSource: "../../icons/nowplaying_clean/warm_repeat_32.png"
            iconText: root.repeatMode === "one" ? "1" : ""
            tooltipText: root.repeatSupported ? "Repetir" : "No soportado por el backend actual"
            selected: root.repeatMode !== "none"
            btnSize: 34
            enabled: root.repeatSupported
            opacity: root.repeatSupported ? 1.0 : 0.35
            onClicked: { if (root.repeatSupported) root.repeatClicked() }
        }
    }
}
