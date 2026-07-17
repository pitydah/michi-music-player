// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../../theme"

Rectangle {
    id: root

    property bool favorite: false

    visible: root.favorite
    width: 16
    height: 16
    radius: 8
    color: MichiTheme.colors.error

    Text {
        anchors.centerIn: parent
        text: "\u2665"
        color: MichiTheme.colors.textOnError
        font.pixelSize: 10
        font.weight: FontWeight.Bold
    }
}
