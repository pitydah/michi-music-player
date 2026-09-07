import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

MenuItem {
    id: root

    objectName: "michiMenuHeader"
    enabled: false
    focusPolicy: Qt.NoFocus

    implicitWidth: Math.max(
        252,
        contentItem.implicitWidth + leftPadding + rightPadding
    )
    implicitHeight: 28

    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.md
    topPadding: MichiSpacing.xxs
    bottomPadding: MichiSpacing.xxs

    contentItem: MichiText {
        text: root.text
        role: "technical"
        technical: true
        color: MichiPalette.textMuted
        font.weight: Font.DemiBold
        font.capitalization: Font.AllUppercase
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Item {
        implicitWidth: 252
        implicitHeight: 28
    }
}
