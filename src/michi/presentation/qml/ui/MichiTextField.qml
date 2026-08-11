import QtQuick
import QtQuick.Controls.Basic
import "../theme"

TextField {
    id: root

    implicitHeight: MichiTheme.controlHeightMedium
    leftPadding: MichiTheme.space12
    rightPadding: MichiTheme.space12

    font.pixelSize: MichiTheme.fontSizeBody
    color: root.enabled ? MichiTheme.textPrimary : MichiTheme.textDisabled
    placeholderTextColor: MichiTheme.textMuted
    selectionColor: MichiTheme.accent

    background: Rectangle {
        radius: MichiTheme.radiusMedium
        color: root.enabled ? MichiTheme.surfacePrimary : MichiTheme.surfaceSecondary
        border.color: root.activeFocus ? MichiTheme.accent : MichiTheme.borderSubtle
        border.width: 1
    }
}
