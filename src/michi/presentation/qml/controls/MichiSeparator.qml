import QtQuick
import QtQuick.Controls.Basic
import "../theme"

MenuSeparator {
    id: root

    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.md
    topPadding: MichiSpacing.xxs
    bottomPadding: MichiSpacing.xxs

    // The separator participates correctly in layout but is never the
    // sole menu-width authority: normal items/menu background provide >=260.
    contentItem: Rectangle {
        implicitWidth: 252
        implicitHeight: 1
        color: MichiSemanticColors.borderSubtle
    }

    background: Item { }
}
