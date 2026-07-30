import QtQuick
import QtQuick.Layouts
import "../theme"
import "."

Item {
    id: root
    objectName: "playbackTransport"

    property bool isPlaying: false
    property bool shuffleEnabled: false
    property string repeatMode: "none"
    property bool commandPending: false
    property bool compact: false
    property bool showShuffle: true
    property bool showPrevious: true
    property bool showNext: true
    property bool showRepeat: true

    signal playRequested()
    signal pauseRequested()
    signal previousRequested()
    signal nextRequested()
    signal shuffleToggled(bool enabled)
    signal repeatCycled(string mode)

    implicitHeight: compact ? 40 : 56
    implicitWidth: compact ? 200 : 280

    RowLayout {
        anchors.centerIn: parent
        spacing: root.compact ? MichiTheme.spacing.xs : MichiTheme.spacing.sm

        MichiIconButton {
            visible: root.showShuffle && !root.compact
            iconSource: "../../icons/nowplaying_clean/warm_shuffle_32.png"
            symbolic: false
            selected: root.shuffleEnabled
            enabled: !root.commandPending
            accessibleName: qsTr("Aleatorio")
            tooltipText: accessibleName
            onClicked: root.shuffleToggled(!root.shuffleEnabled)
        }

        MichiIconButton {
            visible: root.showPrevious
            iconSource: "../../icons/nowplaying_clean/warm_prev_32.png"
            symbolic: false
            enabled: !root.commandPending
            btnSize: root.compact ? 40 : MichiTheme.minimumInteractiveSize
            accessibleName: qsTr("Anterior")
            tooltipText: accessibleName
            onClicked: root.previousRequested()
        }

        MichiIconButton {
            controlObjectName: "playPauseButton"
            iconSource: root.isPlaying
                        ? "../../icons/nowplaying_clean/warm_pause_32.png"
                        : "../../icons/nowplaying_clean/warm_play_32.png"
            symbolic: false
            enabled: !root.commandPending
            circular: true
            selected: true
            btnSize: root.compact ? 40 : 52
            accessibleName: root.isPlaying ? qsTr("Pausar") : qsTr("Reproducir")
            tooltipText: accessibleName
            onClicked: {
                if (root.isPlaying) root.pauseRequested()
                else root.playRequested()
            }
        }

        MichiIconButton {
            visible: root.showNext
            iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
            symbolic: false
            enabled: !root.commandPending
            btnSize: root.compact ? 40 : MichiTheme.minimumInteractiveSize
            accessibleName: qsTr("Siguiente")
            tooltipText: accessibleName
            onClicked: root.nextRequested()
        }

        MichiIconButton {
            controlObjectName: "repeatButton"
            visible: root.showRepeat && !root.compact
            iconSource: "../../icons/nowplaying_clean/warm_repeat_32.png"
            symbolic: false
            selected: root.repeatMode !== "none"
            enabled: !root.commandPending
            accessibleName: root.repeatMode === "one"
                            ? qsTr("Repetir una")
                            : root.repeatMode === "all"
                              ? qsTr("Repetir todas")
                              : qsTr("Repetir")
            tooltipText: accessibleName
            onClicked: {
                var modes = ["none", "all", "one"]
                var idx = modes.indexOf(root.repeatMode)
                var nextMode = modes[(idx + 1) % modes.length]
                root.repeatCycled(nextMode)
            }
        }
    }
}
