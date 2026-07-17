// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../../theme"

Item {
    id: root

    property string title: "Sin álbumes"
    property string message: "No hay álbumes en tu biblioteca. Agrega música para comenzar."
    property string actionText: ""
    signal actionRequested()

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.md
        width: Math.min(parent.width * 0.6, 400)

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        MichiButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.actionText
            variant: "primary"
            visible: root.actionText !== ""
            onClicked: root.actionRequested()
        }
    }
}
