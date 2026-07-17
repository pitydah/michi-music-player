// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../theme"

Menu {
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property var bridge: null

    signal playRequested(string albumKey)
    signal enqueueRequested(string albumKey)
    signal playNextRequested(string albumKey)
    signal detailsRequested(string albumKey)

    MenuItem {
        text: "Reproducir"
        icon.source: ""
        onTriggered: root.playRequested(root.albumKey)
    }

    MenuItem {
        text: "Reproducir siguiente"
        icon.source: ""
        onTriggered: root.playNextRequested(root.albumKey)
    }

    MenuItem {
        text: "Añadir a la cola"
        icon.source: ""
        onTriggered: root.enqueueRequested(root.albumKey)
    }

    MenuSeparator {}

    MenuItem {
        text: "Detalles del álbum"
        icon.source: ""
        onTriggered: root.detailsRequested(root.albumKey)
    }

    MenuItem {
        text: "Ir a la carpeta"
        icon.source: ""
        enabled: root.bridge !== null
        onTriggered: {
            if (root.bridge && root.bridge.revealInFileManager) {
                root.bridge.revealInFileManager(root.albumKey)
            }
        }
    }
}
