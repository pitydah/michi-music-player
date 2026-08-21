import QtQuick
import "../primitives"
import "../theme"

Item {
    id: root
    property string message: ""
    property string tone: "info"
    function show(text, nextTone) {
        message = text
        tone = nextTone || "info"
        hideTimer.restart()
    }
    MichiGlassSurface {
        elevation: "elevated"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: MichiSpacing.xl
        width: Math.min(480, label.implicitWidth + MichiSpacing.xl * 2)
        height: 52
        visible: root.message.length > 0
        MichiText {
            id: label
            anchors.centerIn: parent
            text: root.message
            color: root.tone === "error" ? MichiPalette.error : MichiPalette.textPrimary
        }
    }
    Timer { id: hideTimer; interval: 3500; onTriggered: root.message = "" }
}
