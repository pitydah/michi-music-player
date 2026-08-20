import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Popup {
    id: root
    padding: MichiSpacing.lg
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: MichiMotion.panel } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: MichiMotion.standard } }
    background: MichiGlassSurface { elevation: root.modal ? "modal" : "elevated"; contentPadding: 0 }
}
