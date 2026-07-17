// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../theme"

Rectangle {
    id: root

    property string sectionText: ""
    property int albumCount: 0

    width: parent ? parent.width : 200
    height: 32
    color: MichiTheme.colors.surfaceCard
    radius: MichiTheme.radiusXs

    Text {
        anchors.left: parent.left
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.verticalCenter: parent.verticalCenter
        text: sectionText
        color: MichiTheme.colors.textPrimary
        font.pixelSize: MichiTheme.typography.metaSize
        font.weight: MichiTheme.typography.weightBold
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: MichiTheme.spacing.md
        anchors.verticalCenter: parent.verticalCenter
        text: albumCount > 0 ? albumCount + " álbumes" : ""
        color: MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.captionSize
        visible: albumCount > 0
    }
}
