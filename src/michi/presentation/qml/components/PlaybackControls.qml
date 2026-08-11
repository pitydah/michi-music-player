import QtQuick
import QtQuick.Layouts
import "../ui"

RowLayout {
    id: root
    spacing: 8

    property alias canPlay: playBtn.enabled
    property alias canPause: pauseBtn.enabled
    property alias canStop: stopBtn.enabled
    property alias canPrev: prevBtn.enabled
    property alias canNext: nextBtn.enabled

    signal playClicked()
    signal pauseClicked()
    signal stopClicked()
    signal prevClicked()
    signal nextClicked()

    MichiButton { id: prevBtn; text: "⏮"; variant: "ghost"; onClicked: root.prevClicked() }
    MichiButton { id: playBtn; text: "▶"; onClicked: root.playClicked() }
    MichiButton { id: pauseBtn; text: "⏸"; variant: "secondary"; onClicked: root.pauseClicked() }
    MichiButton { id: stopBtn; text: "■"; variant: "ghost"; onClicked: root.stopClicked() }
    MichiButton { id: nextBtn; text: "⏭"; variant: "ghost"; onClicked: root.nextClicked() }
}
