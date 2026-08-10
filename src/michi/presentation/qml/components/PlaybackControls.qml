import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

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

    Button { id: prevBtn; text: "⏮"; onClicked: root.prevClicked() }
    Button { id: playBtn; text: "▶"; onClicked: root.playClicked() }
    Button { id: pauseBtn; text: "⏸"; onClicked: root.pauseClicked() }
    Button { id: stopBtn; text: "■"; onClicked: root.stopClicked() }
    Button { id: nextBtn; text: "⏭"; onClicked: root.nextClicked() }
}
