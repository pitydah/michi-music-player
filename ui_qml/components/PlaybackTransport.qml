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
    property string variant: "default"
    readonly property bool isBar: variant === "bar"
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

    implicitHeight: root.isBar ? 54 : (root.compact ? 40 : 56)
    implicitWidth: root.isBar ? 270 : (root.compact ? 200 : 280)

    RowLayout {
        anchors.centerIn: parent
        spacing: root.isBar ? 12
                       : root.compact ? MichiTheme.spacing.xs
                                       : MichiTheme.spacing.sm

        MichiIconButton {
            controlObjectName: "shuffleButton"
            visible: root.showShuffle && !root.compact
            iconSource: "../../icons/nowplaying_clean/warm_shuffle_32.png"
            symbolic: false
            iconVisualSize: root.isBar ? 20 : MichiTheme.iconSizeRegular
            btnSize: root.isBar ? 40 : MichiTheme.minimumInteractiveSize
            selected: root.shuffleEnabled
            enabled: !root.commandPending
            accessibleName: qsTr("Aleatorio")
            tooltipText: accessibleName
            onClicked: root.shuffleToggled(!root.shuffleEnabled)
        }

        MichiIconButton {
            controlObjectName: "previousButton"
            visible: root.showPrevious
            iconSource: "../../icons/nowplaying_clean/warm_prev_32.png"
            symbolic: false
            iconVisualSize: root.isBar ? 22 : MichiTheme.iconSizeRegular
            btnSize: root.isBar ? 44 : (root.compact ? 40 : MichiTheme.minimumInteractiveSize)
            enabled: !root.commandPending
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
            iconVisualSize: root.isBar ? 28 : MichiTheme.iconSizeRegular
            enabled: !root.commandPending
            circular: true
            selected: true
            btnSize: root.isBar ? 54 : (root.compact ? 40 : 52)
            accessibleName: root.isPlaying ? qsTr("Pausar") : qsTr("Reproducir")
            tooltipText: accessibleName
            onClicked: {
                if (root.isPlaying) root.pauseRequested()
                else root.playRequested()
            }
        }

        MichiIconButton {
            controlObjectName: "nextButton"
            visible: root.showNext
            iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
            symbolic: false
            iconVisualSize: root.isBar ? 22 : MichiTheme.iconSizeRegular
            btnSize: root.isBar ? 44 : (root.compact ? 40 : MichiTheme.minimumInteractiveSize)
            enabled: !root.commandPending
            accessibleName: qsTr("Siguiente")
            tooltipText: accessibleName
            onClicked: root.nextRequested()
        }

        MichiIconButton {
            controlObjectName: "repeatButton"
            visible: root.showRepeat && !root.compact
            iconSource: "../../icons/nowplaying_clean/warm_repeat_32.png"
            symbolic: false
            iconVisualSize: root.isBar ? 20 : MichiTheme.iconSizeRegular
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
