import QtQuick
import QtQuick.Controls.Basic
import "../theme"

TabBar {
    id: root
    spacing: MichiSpacing.xs
    background: Rectangle {
        radius: MichiRadius.md
        color: MichiSemanticColors.controlSurface
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
    }
}
