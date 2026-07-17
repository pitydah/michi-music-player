// SPDX-FileCopyrightText: 2016 Matthieu Gallien <matthieu_gallien@yahoo.fr>
//   Patrón: Grid delegate con cover + hover indicators (adaptado de KDE Elisa)
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../../components"
import "delegates"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Grid View"
    objectName: "albumGridView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    GridView {
        id: gridView
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        cellWidth: 180
        cellHeight: 240
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        delegate: AlbumGridDelegate {
            width: gridView.cellWidth - MichiTheme.spacing.md
            height: gridView.cellHeight - MichiTheme.spacing.md
            albumKey: model.albumKey || ""
            albumTitle: model.title || ""
            albumArtist: model.artist || ""
            albumYear: model.year || 0
            trackCount: model.trackCount || 0
            onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
            onDoubleClicked: {
                if (root.bridge && root.bridge.playAlbum) {
                    root.bridge.playAlbum(model.albumKey || "")
                }
            }
        }
    }
}
