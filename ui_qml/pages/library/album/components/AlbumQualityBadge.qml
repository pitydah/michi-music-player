// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../../theme"

Rectangle {
    id: root

    property string qualityKind: ""
    property int sampleRate: 0
    property int bitDepth: 0

    width: MichiTheme.spacing.sm
    height: MichiTheme.spacing.sm
    radius: MichiTheme.radius.xs
    visible: qualityKind !== ""

    color: {
        switch (root.qualityKind) {
            case "dsd": return MichiTheme.colors.success
            case "hires": return MichiTheme.colors.accentBlue
            case "lossless": return MichiTheme.colors.badgeActiveText
            case "lossy": return MichiTheme.colors.textMuted
            default: return MichiTheme.colors.badgeMutedBg
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(parent.color.r, parent.color.g, parent.color.b, 0.3)
    }
}
