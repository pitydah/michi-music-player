import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Item {
    id: root
    property string message: ""
    property string tone: "info"
    property string actionText: ""
    signal actionRequested()
    function show(text, nextTone) {
        message = text
        tone = nextTone || "info"
        actionText = ""
        hideTimer.restart()
    }
    function showWithAction(text, action, nextTone) {
        message = text
        actionText = action
        tone = nextTone || "info"
        hideTimer.restart()
    }
    MichiGlassSurface {
        elevation: "elevated"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: MichiSpacing.xl
        width: Math.min(520, toastRow.implicitWidth + MichiSpacing.xl * 2)
        height: 52
        opacity: root.message.length > 0 ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
        }
        RowLayout {
            id: toastRow
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.lg
            anchors.rightMargin: MichiSpacing.sm
            spacing: MichiSpacing.md
            MichiText {
                id: label
                Layout.fillWidth: true
                text: root.message
                elide: Text.ElideRight
                color: root.tone === "error" ? MichiPalette.error : MichiPalette.textPrimary
            }
            MichiButton {
                visible: root.actionText.length > 0
                text: root.actionText
                variant: "ghost"
                onClicked: {
                    root.actionRequested()
                    root.message = ""
                }
            }
        }
    }
    Timer { id: hideTimer; interval: 3500; onTriggered: root.message = "" }
}
