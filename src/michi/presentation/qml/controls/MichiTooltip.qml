import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

ToolTip {
    id: root
    delay: 550
    timeout: 4000
    padding: MichiSpacing.sm
    contentItem: MichiText { text: root.text; role: "caption"; color: MichiPalette.textPrimary }
    background: MichiGlassSurface { elevation: "elevated"; contentPadding: 0; radius: MichiRadius.sm }
}
