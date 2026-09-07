import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

// MichiMenuHeader (R10 — Context Menu System V2): header de sección
// visible dentro de un menú contextual. Sustituye al separador mudo como
// única jerarquía: agrupa visualmente familias de acciones (V4 §37-42).
MenuItem {
    id: root

    objectName: "michiMenuHeader"
    enabled: false
    focusPolicy: Qt.NoFocus

    contentItem: MichiText {
        text: root.text
        role: "technical"
        technical: true
        color: MichiPalette.textMuted
        font.weight: Font.DemiBold
        font.capitalization: Font.AllUppercase
        verticalAlignment: Text.AlignVCenter
        leftPadding: MichiSpacing.sm + 2
        rightPadding: MichiSpacing.sm + 2
    }

    background: Item {}
}
