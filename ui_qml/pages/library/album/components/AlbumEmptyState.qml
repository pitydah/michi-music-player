// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import "../../../../components"

MichiEmptyState {
    id: root

    Accessible.role: Accessible.Pane
    Accessible.name: root.title
    objectName: "albumEmptyState"
    focus: true

    property string actionText: ""

    signal actionRequested()

    title: qsTr("Sin álbumes")
    message: qsTr("No hay álbumes en tu biblioteca. Agrega música para comenzar.")
    iconName: "albums"
    primaryActionText: root.actionText

    onPrimaryActionRequested: root.actionRequested()
}
