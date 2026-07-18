// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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

    function scrollToAlbum(albumKey) {
        if (!root.albumModel) return
        for (var i = 0; i < root.albumModel.count; i++) {
            var item = root.albumModel.get(i)
            if (item.albumKey === albumKey) {
                listView.positionViewAtIndex(i, ListView.Contain)
                return
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md

                Text {
                    text: root.groupByDecade ? "Agrupado por década" : qsTr("Agrupado por año")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: root.groupByDecade ? "Año" : qsTr("Década")
                    variant: "ghost"
                    implicitHeight: 24
                    onClicked: root.groupByDecade = !root.groupByDecade
                }
            }
        }

        ListView {
            focusPolicy: Qt.StrongFocus
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
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
}
