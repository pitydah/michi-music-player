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
            controlObjectName: "nowPlayingShuffleButton"
            visible: !root.compact || root.isBar
            iconKey: "shuffle"
            symbolic: true
            iconVisualSize: root.isBar ? 20 : MichiTheme.iconSizeRegular
            btnSize: root.isBar ? 40 : MichiTheme.minimumInteractiveSize
            selected: root.shuffleEnabled
            enabled: !root.commandPending
            disabledVisualOpacity: 0.55
            accessibleName: qsTr("Aleatorio")
            tooltipText: accessibleName
            onClicked: root.shuffleToggled(!root.shuffleEnabled)
        }

        MichiIconButton {
            controlObjectName: "nowPlayingPreviousButton"
            visible: !root.compact || root.isBar
            iconKey: "previous"
            symbolic: true
            iconVisualSize: root.isBar ? 22 : MichiTheme.iconSizeRegular
            btnSize: root.isBar ? 44 : (root.compact ? 40 : MichiTheme.minimumInteractiveSize)
            enabled: !root.commandPending
            disabledVisualOpacity: 0.55
            accessibleName: qsTr("Anterior")
            tooltipText: accessibleName
            onClicked: root.previousRequested()
        }

        MichiIconButton {
            controlObjectName: "nowPlayingPlayPauseButton"
            iconKey: root.isPlaying ? "pause" : "play"
            symbolic: true
            iconVisualSize: root.isBar ? 28 : MichiTheme.iconSizeRegular
            enabled: !root.commandPending
            disabledVisualOpacity: 0.55
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
            controlObjectName: "nowPlayingNextButton"
            visible: !root.compact || root.isBar
            iconKey: "next"
            symbolic: true
            iconVisualSize: root.isBar ? 22 : MichiTheme.iconSizeRegular
            btnSize: root.isBar ? 44 : (root.compact ? 40 : MichiTheme.minimumInteractiveSize)
            enabled: !root.commandPending
            disabledVisualOpacity: 0.55
            accessibleName: qsTr("Siguiente")
            tooltipText: accessibleName
            onClicked: root.nextRequested()
        }

        MichiIconButton {
            controlObjectName: "nowPlayingRepeatButton"
            visible: !root.compact || root.isBar
            iconKey: root.repeatMode === "one" ? "repeat_one" : "repeat"
            symbolic: true
            iconVisualSize: root.isBar ? 20 : MichiTheme.iconSizeRegular
            selected: root.repeatMode !== "none"
            enabled: !root.commandPending
            disabledVisualOpacity: 0.55
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
