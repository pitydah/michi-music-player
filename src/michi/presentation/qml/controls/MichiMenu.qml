import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Menu {
    id: root
    padding: MichiSpacing.xs
    delegate: MenuItem {
        id: menuItem
        implicitHeight: MichiMetrics.controlMedium
        leftPadding: MichiSpacing.md
        rightPadding: MichiSpacing.md
        contentItem: MichiText {
            text: menuItem.text
            role: "secondary"
            color: menuItem.enabled ? MichiPalette.textPrimary : MichiPalette.textDisabled
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: MichiRadius.sm
            color: menuItem.highlighted ? MichiSemanticColors.surfaceHover : "transparent"
        }
    }
    background: MichiGlassSurface { elevation: "elevated"; contentPadding: 0; radius: MichiRadius.md }
}
