import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Dialog {
    id: root
    modal: true
    focus: true
    padding: MichiSpacing.xl
    closePolicy: Popup.CloseOnEscape
    background: MichiGlassSurface { elevation: "modal"; contentPadding: 0 }
    header: Item {
        implicitHeight: dialogTitle.implicitHeight + MichiSpacing.lg * 2
        MichiText {
            id: dialogTitle
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: MichiSpacing.lg
            anchors.rightMargin: MichiSpacing.lg
            text: root.title
            role: "section"
        }
    }
}
