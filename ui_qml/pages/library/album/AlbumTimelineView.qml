// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"
import "delegates"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Timeline View"
    objectName: "albumTimelineView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    property bool groupByDecade: false
    signal albumClicked(string albumKey, string title, string artist, int year)

    ListView {
        focusPolicy: Qt.StrongFocus
        id: listView
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        section.property: root.groupByDecade ? "decade" : "year"
        section.labelPositioning: ViewSection.CurrentLabelAtStart | ViewSection.InlineLabels
        section.delegate: AlbumSectionHeader {
            width: listView.width
            sectionText: {
                if (root.groupByDecade && section > 0) {
                    return section + "s"
                } else if (section > 0) {
                    return section
                }
                return "Año desconocido"
            }
        }

        delegate: AlbumRowDelegate {
            width: listView.width
            albumKey: model.albumKey || ""
            albumTitle: model.title || ""
            albumArtist: model.artist || ""
            albumYear: model.year || 0
            trackCount: model.trackCount || 0
            onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
        }
    }
}
