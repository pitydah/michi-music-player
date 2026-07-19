// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

Item {
    id: root
    objectName: "albumTimelineView"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Línea de tiempo de álbumes")

    property var albumModel: null
    property var bridge: null
    property bool groupByDecade: false
    signal albumClicked(string albumKey, string title, string artist, int year)

    function scrollToAlbum(albumKey) {
        if (!root.albumModel || !root.albumModel.get) return
        for (var i = 0; i < root.albumModel.count; i++) {
            var item = root.albumModel.get(i)
            if ((item.albumKey || "") === albumKey) {
                listView.currentIndex = i
                listView.positionViewAtIndex(i, ListView.Center)
                return
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.surfaceCard
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.lg
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.md

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Text {
                        text: root.groupByDecade ? qsTr("Archivo por década") : qsTr("Archivo por año")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }
                    Text {
                        text: qsTr("Recorre la evolución cronológica de tu colección")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                    }
                }

                Rectangle {
                    width: 188
                    height: 34
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceInput
                    border.width: MichiTheme.borderWidth
                    border.color: MichiTheme.colors.borderCard

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2

                        Repeater {
                            model: [qsTr("Años"), qsTr("Décadas")]
                            Rectangle {
                                required property int index
                                required property string modelData
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: MichiTheme.radius.sm
                                color: (index === 1) === root.groupByDecade
                                       ? MichiTheme.colors.accentSelection
                                       : timelineModeMouse.containsMouse
                                         ? MichiTheme.colors.surfaceHover
                                         : "transparent"
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: (index === 1) === root.groupByDecade
                                           ? MichiTheme.colors.accentBlue
                                           : MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }
                                MouseArea {
                                    id: timelineModeMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.groupByDecade = index === 1
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.surfaceElevation0
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle
            clip: true

            ListView {
                id: listView
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                model: root.albumModel
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                spacing: MichiTheme.spacing.xs
                activeFocusOnTab: true
                focus: true
                keyNavigationWraps: false

                section.property: root.groupByDecade ? "decade" : "year"
                section.criteria: ViewSection.FullString
                section.labelPositioning: ViewSection.CurrentLabelAtStart | ViewSection.InlineLabels
                section.delegate: Item {
                    required property string section
                    width: listView.width
                    height: 54
                    z: 4

                    Rectangle {
                        anchors.fill: parent
                        color: MichiTheme.colors.surfaceToolbar
                        radius: MichiTheme.radius.md
                        border.width: MichiTheme.borderWidth
                        border.color: MichiTheme.colors.borderSubtle

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: MichiTheme.spacing.lg
                            anchors.rightMargin: MichiTheme.spacing.lg

                            Rectangle {
                                width: 10; height: 10; radius: 5
                                color: MichiTheme.colors.accentPrimary
                            }
                            Text {
                                text: {
                                    var numeric = Number(section)
                                    if (!numeric) return qsTr("Fecha desconocida")
                                    return root.groupByDecade ? numeric + "s" : numeric
                                }
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.sectionTitleSize
                                font.weight: MichiTheme.typography.weightBold
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: root.groupByDecade ? qsTr("Década") : qsTr("Año")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.captionSize
                                font.capitalization: Font.AllUppercase
                            }
                        }
                    }
                }

                Keys.onReturnPressed: {
                    if (root.albumModel && root.albumModel.get && currentIndex >= 0) {
                        var item = root.albumModel.get(currentIndex)
                        root.albumClicked(item.albumKey || "", item.title || "", item.artist || "", item.year || 0)
                    }
                }
                Keys.onEnterPressed: {
                    if (root.albumModel && root.albumModel.get && currentIndex >= 0) {
                        var item = root.albumModel.get(currentIndex)
                        root.albumClicked(item.albumKey || "", item.title || "", item.artist || "", item.year || 0)
                    }
                }
                Keys.onSpacePressed: {
                    if (root.albumModel && root.albumModel.get && currentIndex >= 0 && root.bridge && root.bridge.playAlbum) {
                        var item = root.albumModel.get(currentIndex)
                        root.bridge.playAlbum(item.albumKey || "")
                    }
                }

                ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

                delegate: Item {
                    id: timelineRow
                    width: listView.width
                    height: 82
                    readonly property bool selected: ListView.isCurrentItem

                    Accessible.role: Accessible.Button
                    Accessible.name: (model.year || qsTr("Sin año")) + ": " + (model.title || qsTr("Álbum sin título"))
                    Accessible.onPressAction: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)

                    Rectangle {
                        id: line
                        x: 35
                        y: -MichiTheme.spacing.xs
                        width: 2
                        height: parent.height + MichiTheme.spacing.sm
                        color: MichiTheme.colors.borderCard
                    }

                    Rectangle {
                        x: 27
                        anchors.verticalCenter: parent.verticalCenter
                        width: 18
                        height: 18
                        radius: 9
                        color: timelineRow.selected || rowMouse.containsMouse
                               ? MichiTheme.colors.accentPrimary
                               : MichiTheme.colors.surfaceElevation4
                        border.width: 3
                        border.color: MichiTheme.colors.bgContent
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 58
                        anchors.right: parent.right
                        anchors.rightMargin: MichiTheme.spacing.sm
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        radius: MichiTheme.radius.md
                        color: timelineRow.selected
                               ? MichiTheme.colors.accentSelection
                               : rowMouse.containsMouse
                                 ? MichiTheme.colors.surfaceCardHover
                                 : MichiTheme.colors.surfaceCard
                        border.width: timelineRow.selected ? MichiTheme.borderWidth : 0
                        border.color: MichiTheme.colors.borderActive

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            spacing: MichiTheme.spacing.md

                            CoverImage {
                                Layout.preferredWidth: 60
                                Layout.preferredHeight: 60
                                coverRadius: MichiTheme.radius.sm
                                coverKey: model.coverKey || model.albumKey || ""
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    Layout.fillWidth: true
                                    text: model.title || qsTr("Álbum sin título")
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: model.artist || qsTr("Artista desconocido")
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: (model.trackCount || 0) + " " + qsTr("canciones")
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 58
                                Layout.preferredHeight: 28
                                radius: MichiTheme.radius.pill
                                color: MichiTheme.colors.surfaceInput
                                visible: (model.year || 0) > 0
                                Text {
                                    anchors.centerIn: parent
                                    text: model.year || ""
                                    color: MichiTheme.colors.textNormal
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 36
                                Layout.preferredHeight: 36
                                radius: 18
                                color: rowMouse.containsMouse || timelineRow.selected
                                       ? MichiTheme.colors.accentPrimary
                                       : MichiTheme.colors.surfaceElevation3
                                Text {
                                    anchors.centerIn: parent
                                    text: "▶"
                                    color: rowMouse.containsMouse || timelineRow.selected
                                           ? MichiTheme.colors.textOnAccent
                                           : MichiTheme.colors.textSecondary
                                    font.pixelSize: 12
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: function(mouse) {
                                        mouse.accepted = true
                                        if (root.bridge && root.bridge.playAlbum)
                                            root.bridge.playAlbum(model.albumKey || "")
                                    }
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        anchors.leftMargin: 58
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onPressed: listView.currentIndex = index
                        onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                        onDoubleClicked: {
                            if (root.bridge && root.bridge.playAlbum)
                                root.bridge.playAlbum(model.albumKey || "")
                        }
                    }
                }

                footer: Item {
                    width: listView.width
                    height: root.albumModel && root.albumModel.hasMore ? 48 : MichiTheme.spacing.md
                    MichiButton {
                        anchors.centerIn: parent
                        visible: root.albumModel && root.albumModel.hasMore
                        enabled: root.albumModel && !root.albumModel.loadingMore
                        text: root.albumModel && root.albumModel.loadingMore ? qsTr("Cargando…") : qsTr("Cargar más")
                        variant: "ghost"
                        onClicked: root.albumModel.fetchMore()
                    }
                }
            }
        }
    }
}
