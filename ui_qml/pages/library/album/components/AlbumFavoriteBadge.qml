// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../theme"

Rectangle {
    id: root

    property bool favorite: false

    visible: root.favorite
    width: MichiTheme.spacing.lg
    height: MichiTheme.spacing.lg
    radius: MichiTheme.radius.md
    color: MichiTheme.colors.error

    Text {
        anchors.centerIn: parent
        text: "\u2665"
        color: MichiTheme.colors.textOnError
        font.pixelSize: MichiTheme.typography.badgeSize
        font.weight: MichiTheme.typography.weightBold
    }
}
