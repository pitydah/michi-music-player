import QtQuick
import QtQuick.Layouts
import "../controls"

RowLayout {
    id: root
    spacing: 8

    property bool playing: false
    property bool canPlay: false
    property bool canPause: false
    property bool canStop: false
    property bool canPrev: false
    property bool canNext: false

    signal playClicked()
    signal pauseClicked()
    signal stopClicked()
    signal prevClicked()
    signal nextClicked()

    MichiIconButton {
        iconName: "previous"
        accessibleName: "Previous track"
        enabled: root.canPrev
        onClicked: root.prevClicked()
    }
    MichiIconButton {
        iconName: root.playing ? "pause" : "play"
        accessibleName: root.playing ? "Pause" : "Play"
        selected: root.playing
        enabled: root.playing ? root.canPause : root.canPlay
        implicitWidth: MichiMetrics.controlLarge
        implicitHeight: MichiMetrics.controlLarge
        onClicked: root.playing ? root.pauseClicked() : root.playClicked()
    }
    MichiIconButton {
        iconName: "stop"
        accessibleName: "Stop"
        enabled: root.canStop
        onClicked: root.stopClicked()
    }
    MichiIconButton {
        iconName: "next"
        accessibleName: "Next track"
        enabled: root.canNext
        onClicked: root.nextClicked()
    }
}
